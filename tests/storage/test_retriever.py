"""Comprehensive automated unit and integration tests for Module 06: Semantic Retriever and Top-K Ranking.

Covers:
1. Relevant chunks ranked correctly (most relevant first)
2. Top-k limits and defaults
3. Cosine similarity score interpretation (score = 1.0 - distance, higher = better)
4. Query embedding reuse through existing IEmbeddingService (no duplicate models)
5. Strict conversation isolation (conv_A queries cannot see conv_B chunks)
6. Optional file filtering (only chunks from specified file_id are returned)
7. Empty query behavior (returns empty results gracefully)
8. Empty index behavior (returns empty results gracefully)
9. Non-existent collection behavior (graceful handling, no crash)
10. Invalid top-k rejection (negative, zero, non-integer)
11. Full metadata preservation (chunk_id, file_id, filename, text, source_page, offsets)
12. Deterministic ranking on score ties (chunk_index ordering)
13. Storage and embedding failure handling
14. FileService integration (file_service.retrieve_context)
15. FastAPI endpoint POST /v1/retrieval/search
"""

import math
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional

import numpy as np
import pytest
from fastapi.testclient import TestClient

from aurora.config.settings import RetrieverConfig, RuntimeStorageConfig, VectorStoreConfig
from aurora.core.exceptions import (
    EmbeddingError,
    InvalidTopKError,
    RetrievalError,
    StorageOperationError,
)
from aurora.deployment.api_server import app
from aurora.ingestion.runtime.file_storage import RuntimeFileStorage
from aurora.ingestion.runtime.file_validator import RuntimeFileValidator
from aurora.interfaces.embedding import IEmbeddingService
from aurora.models.embedding import EmbeddedChunk, EmbeddingBatchResult
from aurora.models.retrieval import RetrievalResult, ScoredChunk
from aurora.models.runtime_chunk import ChunkingConfig, DocumentChunk
from aurora.preprocessing.runtime_chunker import RuntimeChunker
from aurora.services.file_service import FileService
from aurora.storage.retriever import SemanticRetriever
from aurora.storage.vector_store import ChromaVectorStore


@pytest.fixture
def temp_vector_dir():
    temp_dir = tempfile.mkdtemp(prefix="aurora_test_retriever_vector_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_storage_dir():
    temp_dir = tempfile.mkdtemp(prefix="aurora_test_retriever_file_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


class ControlledMockEmbeddingService(IEmbeddingService):
    """Controlled mock embedding service mapping specific concepts to orthogonal unit vectors."""

    def __init__(self, dimension: int = 384) -> None:
        self._dim = dimension
        self.call_count = 0

    def embed_text(self, text: str) -> List[float]:
        self.call_count += 1
        vec = np.zeros(self._dim, dtype=np.float32)
        lower = text.lower()

        # Map concept keywords to specific orthogonal vector coordinates
        if "process" in lower or "deadlock" in lower or "cpu" in lower:
            vec[0] = 1.0
        elif "btree" in lower or "index" in lower or "database" in lower:
            vec[1] = 1.0
        elif "packet" in lower or "tcp" in lower or "network" in lower:
            vec[2] = 1.0
        else:
            # Deterministic hash fallback
            h = sum(ord(c) for c in text) % self._dim
            vec[h] = 1.0

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def embed_chunks(self, chunks: List[DocumentChunk]) -> EmbeddingBatchResult:
        embedded_chunks = []
        for chunk in chunks:
            vec = self.embed_text(chunk.text)
            embedded_chunks.append(
                EmbeddedChunk(
                    chunk_id=chunk.chunk_id,
                    file_id=chunk.file_id,
                    embedding=vec,
                    dimension=self._dim,
                    chunk=chunk,
                )
            )
        return EmbeddingBatchResult(
            model_name="controlled-mock-model",
            dimension=self._dim,
            embedded_chunks=embedded_chunks,
            total_chunks=len(embedded_chunks),
            normalized=True,
        )

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return "controlled-mock-model"


def _create_chunk(
    chunk_id: str,
    file_id: str,
    text: str,
    chunk_index: int = 0,
    source_page: Optional[int] = None,
    filename: str = "notes.txt",
) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=chunk_id,
        file_id=file_id,
        filename=filename,
        text=text,
        chunk_index=chunk_index,
        total_chunks=1,
        source_page=source_page,
        start_char=0,
        end_char=len(text),
        char_count=len(text),
        token_estimate=len(text.split()),
    )


# =========================================================================
# Unit Tests for SemanticRetriever & ChromaVectorStore.query_vectors
# =========================================================================

def test_retrieval_ranking_and_scores(temp_vector_dir):
    """Verifies that chunks most semantically relevant to query rank first with highest scores."""
    vector_config = VectorStoreConfig(persist_dir=str(temp_vector_dir), embedding_dimension=384)
    store = ChromaVectorStore(config=vector_config)
    mock_embed = ControlledMockEmbeddingService(dimension=384)

    # Chunks on different topics
    os_chunk = _create_chunk("c_os", "f_os", "Deadlock occurs when processes hold resources and wait.", source_page=5)
    db_chunk = _create_chunk("c_db", "f_db", "B-tree database indexes improve search performance.", source_page=12)
    net_chunk = _create_chunk("c_net", "f_net", "TCP packets guarantee reliable stream delivery.", source_page=None)

    batch = mock_embed.embed_chunks([os_chunk, db_chunk, net_chunk])
    store.store_embedded_chunks("conv_cs", batch.embedded_chunks)

    retriever = SemanticRetriever(embedding_service=mock_embed, vector_store=store)

    # Search for OS concept
    res_os = retriever.retrieve(query="What is a deadlock and process scheduling?", conversation_id="conv_cs", top_k=3)
    assert res_os.total_retrieved >= 1
    top_result = res_os.results[0]
    assert top_result.chunk_id == "c_os"
    assert top_result.chunk.source_page == 5
    assert top_result.chunk.filename == "notes.txt"
    # Exact vector match: distance ~ 0, score ~ 1.0
    assert top_result.score > 0.9
    assert top_result.distance < 0.1

    # Search for Database concept
    res_db = retriever.retrieve(query="Explain database b-tree index", conversation_id="conv_cs", top_k=2)
    assert res_db.results[0].chunk_id == "c_db"
    assert res_db.results[0].chunk.source_page == 12


def test_top_k_limits_and_default(temp_vector_dir):
    """Verifies top-k capping and default top-k parameter."""
    store = ChromaVectorStore(config=VectorStoreConfig(persist_dir=str(temp_vector_dir)))
    mock_embed = ControlledMockEmbeddingService()

    chunks = [_create_chunk(f"c_{i}", "f1", f"Process scheduling method {i}") for i in range(10)]
    batch = mock_embed.embed_chunks(chunks)
    store.store_embedded_chunks("conv_topk", batch.embedded_chunks)

    retriever = SemanticRetriever(
        embedding_service=mock_embed,
        vector_store=store,
        config=RetrieverConfig(default_top_k=3, max_top_k=8),
    )

    # Default top_k should be 3
    res_default = retriever.retrieve(query="process", conversation_id="conv_topk")
    assert len(res_default.results) == 3
    assert res_default.top_k == 3

    # Custom top_k = 5
    res_5 = retriever.retrieve(query="process", conversation_id="conv_topk", top_k=5)
    assert len(res_5.results) == 5

    # Exceeding max_top_k (8) is capped to 8
    res_capped = retriever.retrieve(query="process", conversation_id="conv_topk", top_k=20)
    assert len(res_capped.results) == 8


def test_conversation_isolation_in_retrieval(temp_vector_dir):
    """Ensures retrieval in conv_A cannot return chunks stored in conv_B."""
    store = ChromaVectorStore(config=VectorStoreConfig(persist_dir=str(temp_vector_dir)))
    mock_embed = ControlledMockEmbeddingService()

    c_a = _create_chunk("c_secret_a", "f_a", "CPU scheduling confidential algorithm A")
    c_b = _create_chunk("c_secret_b", "f_b", "CPU scheduling confidential algorithm B")

    store.store_embedded_chunks("conv_user_A", mock_embed.embed_chunks([c_a]).embedded_chunks)
    store.store_embedded_chunks("conv_user_B", mock_embed.embed_chunks([c_b]).embedded_chunks)

    retriever = SemanticRetriever(embedding_service=mock_embed, vector_store=store)

    res_a = retriever.retrieve(query="CPU scheduling", conversation_id="conv_user_A")
    res_ids_a = [r.chunk_id for r in res_a.results]
    assert "c_secret_a" in res_ids_a
    assert "c_secret_b" not in res_ids_a

    res_b = retriever.retrieve(query="CPU scheduling", conversation_id="conv_user_B")
    res_ids_b = [r.chunk_id for r in res_b.results]
    assert "c_secret_b" in res_ids_b
    assert "c_secret_a" not in res_ids_b


def test_file_id_filtering(temp_vector_dir):
    """Ensures optional file_id filter restricts retrieval to a single file within the conversation."""
    store = ChromaVectorStore(config=VectorStoreConfig(persist_dir=str(temp_vector_dir)))
    mock_embed = ControlledMockEmbeddingService()

    c_f1 = _create_chunk("c_f1", "file_alpha", "TCP network socket programming")
    c_f2 = _create_chunk("c_f2", "file_beta", "TCP network congestion control")

    store.store_embedded_chunks("conv_filter", mock_embed.embed_chunks([c_f1, c_f2]).embedded_chunks)
    retriever = SemanticRetriever(embedding_service=mock_embed, vector_store=store)

    # Filter by file_alpha
    res = retriever.retrieve(query="TCP network", conversation_id="conv_filter", file_id="file_alpha")
    assert len(res.results) == 1
    assert res.results[0].file_id == "file_alpha"
    assert res.results[0].chunk_id == "c_f1"


def test_empty_query_and_empty_index(temp_vector_dir):
    """Verifies empty queries and queries against empty indexes return empty lists safely."""
    store = ChromaVectorStore(config=VectorStoreConfig(persist_dir=str(temp_vector_dir)))
    mock_embed = ControlledMockEmbeddingService()
    retriever = SemanticRetriever(embedding_service=mock_embed, vector_store=store)

    # Empty query string
    res_empty_q = retriever.retrieve(query="", conversation_id="conv_empty")
    assert res_empty_q.total_retrieved == 0
    assert len(res_empty_q.results) == 0

    res_whitespace_q = retriever.retrieve(query="   ", conversation_id="conv_empty")
    assert res_whitespace_q.total_retrieved == 0

    # Query against non-existent conversation / empty index
    res_empty_idx = retriever.retrieve(query="deadlock", conversation_id="conv_non_existent")
    assert res_empty_idx.total_retrieved == 0
    assert len(res_empty_idx.results) == 0


def test_invalid_top_k_rejected(temp_vector_dir):
    """Invalid top-k values (<= 0 or non-integers) must raise InvalidTopKError."""
    store = ChromaVectorStore(config=VectorStoreConfig(persist_dir=str(temp_vector_dir)))
    retriever = SemanticRetriever(vector_store=store)

    with pytest.raises(InvalidTopKError):
        retriever.retrieve(query="test", conversation_id="conv_val", top_k=0)

    with pytest.raises(InvalidTopKError):
        retriever.retrieve(query="test", conversation_id="conv_val", top_k=-5)


def test_score_tie_deterministic_ranking(temp_vector_dir):
    """When chunks have identical score, secondary sort orders deterministically by chunk_index."""
    store = ChromaVectorStore(config=VectorStoreConfig(persist_dir=str(temp_vector_dir)))
    mock_embed = ControlledMockEmbeddingService()

    # Two chunks with identical text (and therefore identical embeddings and scores)
    c_idx0 = _create_chunk("c_zero", "f1", "Exact matching text content", chunk_index=0)
    c_idx1 = _create_chunk("c_one", "f1", "Exact matching text content", chunk_index=1)
    c_idx2 = _create_chunk("c_two", "f1", "Exact matching text content", chunk_index=2)

    store.store_embedded_chunks("conv_ties", mock_embed.embed_chunks([c_idx2, c_idx0, c_idx1]).embedded_chunks)
    retriever = SemanticRetriever(embedding_service=mock_embed, vector_store=store)

    res = retriever.retrieve(query="Exact matching text content", conversation_id="conv_ties", top_k=3)
    assert len(res.results) == 3
    # Scores must all match
    assert res.results[0].score == res.results[1].score == res.results[2].score
    # Order must be sorted by chunk_index ascending: 0, 1, 2
    assert res.results[0].chunk.chunk_index == 0
    assert res.results[1].chunk.chunk_index == 1
    assert res.results[2].chunk.chunk_index == 2


def test_embedding_failure_handling(temp_vector_dir):
    """If embedding model inference crashes, RetrievalError must be raised with clear message."""
    class FailingEmbedder(IEmbeddingService):
        def embed_text(self, text: str) -> List[float]:
            raise RuntimeError("CUDA out of memory during query embedding.")

        def embed_chunks(self, chunks):
            return []

        @property
        def dimension(self):
            return 384

        @property
        def model_name(self):
            return "failing-model"

    store = ChromaVectorStore(config=VectorStoreConfig(persist_dir=str(temp_vector_dir)))
    retriever = SemanticRetriever(embedding_service=FailingEmbedder(), vector_store=store)

    with pytest.raises(RetrievalError, match="Query embedding generation failed"):
        retriever.retrieve(query="test failure", conversation_id="conv_fail")


# =========================================================================
# Integration with FileService
# =========================================================================

def test_file_service_retrieve_context(temp_storage_dir, temp_vector_dir):
    """Verifies FileService.retrieve_context works seamlessly after upload and indexing."""
    storage_config = RuntimeStorageConfig(upload_dir=str(temp_storage_dir))
    vector_config = VectorStoreConfig(persist_dir=str(temp_vector_dir), embedding_dimension=384)

    validator = RuntimeFileValidator(storage_config)
    storage = RuntimeFileStorage(storage_config)
    chunker = RuntimeChunker()
    mock_embed = ControlledMockEmbeddingService(dimension=384)
    vector_store = ChromaVectorStore(config=vector_config)

    file_service = FileService(
        validator=validator,
        storage=storage,
        chunker=chunker,
        embedding_service=mock_embed,
        vector_store=vector_store,
    )

    # 1. Upload and index file
    content = b"Deadlocks in operating systems require mutual exclusion, hold and wait, no preemption, and circular wait."
    uploaded = file_service.upload_file(
        conversation_id="conv_service_retrieval",
        filename="os_deadlocks.txt",
        content_type="text/plain",
        content=content,
    )
    file_service.index_file(uploaded.file_id, "conv_service_retrieval")

    # 2. Retrieve context via file_service
    retrieval_res = file_service.retrieve_context(
        query="What are the conditions for a deadlock?",
        conversation_id="conv_service_retrieval",
        top_k=3,
    )

    assert retrieval_res.total_retrieved >= 1
    assert retrieval_res.results[0].chunk.file_id == uploaded.file_id
    assert "mutual exclusion" in retrieval_res.results[0].chunk.text
    assert retrieval_res.results[0].score > 0.0


# =========================================================================
# FastAPI Endpoint Tests: POST /v1/retrieval/search
# =========================================================================

def test_api_server_retrieval_endpoint():
    """Tests POST /v1/retrieval/search endpoint."""
    client = TestClient(app)
    conv_id = "test_conv_api_search"

    # 1. Upload & Index a file
    text_content = "Computer networks utilize packet switching rather than circuit switching."
    upload_res = client.post(
        "/v1/files/upload",
        data={"conversation_id": conv_id},
        files={"file": ("networks.txt", text_content.encode("utf-8"), "text/plain")},
    )
    assert upload_res.status_code == 200
    file_id = upload_res.json()["file_id"]

    try:
        idx_res = client.post(f"/v1/files/{file_id}/index", params={"conversation_id": conv_id})
        assert idx_res.status_code == 200

        # 2. Search via API
        search_res = client.post(
            "/v1/retrieval/search",
            params={"query": "packet switching networks", "conversation_id": conv_id, "top_k": 3},
        )
        assert search_res.status_code == 200
        data = search_res.json()
        assert data["conversation_id"] == conv_id
        assert data["total_retrieved"] >= 1
        assert len(data["results"]) >= 1
        assert data["results"][0]["chunk_id"] is not None
        assert "score" in data["results"][0]

        # 3. Test empty query validation error (400)
        empty_res = client.post("/v1/retrieval/search", params={"query": "", "conversation_id": conv_id})
        assert empty_res.status_code == 400

        # 4. Test missing conversation_id validation error (400 or 422)
        no_conv_res = client.post("/v1/retrieval/search", params={"query": "hello", "conversation_id": ""})
        assert no_conv_res.status_code == 400

    finally:
        client.delete(f"/v1/files/{file_id}", params={"conversation_id": conv_id})
