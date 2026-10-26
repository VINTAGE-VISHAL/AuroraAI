"""Comprehensive automated unit and integration tests for Module 05: Persistent Vector Store.

Covers:
1. Storing a batch of embedded chunks
2. Persistent storage across store reload/reinitialization
3. Similarity-search-ready vector and metadata format
4. File and conversation isolation
5. Deleting one file without affecting another
6. Re-indexing without duplicates (upsert behavior)
7. Empty batches handling
8. Incorrect vector dimensions rejection
9. NaN or infinite vector rejection
10. Duplicate chunk IDs handling
11. Storage failure handling
12. FileService integration for upload -> extract -> chunk -> embed -> store
13. FastAPI POST /v1/files/{file_id}/index endpoint
14. File deletion triggers vector store cleanup
"""

import math
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional

import chromadb
import numpy as np
import pytest
from fastapi.testclient import TestClient

from aurora.config.settings import EmbeddingConfig, RuntimeStorageConfig, VectorStoreConfig
from aurora.core.exceptions import (
    MalformedVectorError,
    RuntimeFileNotFoundError,
    VectorDimensionMismatchError,
    VectorStoreError,
)
from aurora.deployment.api_server import app
from aurora.ingestion.runtime.file_storage import RuntimeFileStorage
from aurora.ingestion.runtime.file_validator import RuntimeFileValidator
from aurora.interfaces.embedding import IEmbeddingService
from aurora.models.embedding import EmbeddedChunk, EmbeddingBatchResult
from aurora.models.runtime_chunk import ChunkingConfig, DocumentChunk
from aurora.preprocessing.runtime_chunker import RuntimeChunker
from aurora.services.file_service import FileService
from aurora.storage.vector_store import ChromaVectorStore


@pytest.fixture
def temp_vector_dir():
    temp_dir = tempfile.mkdtemp(prefix="aurora_test_vector_store_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_storage_dir():
    temp_dir = tempfile.mkdtemp(prefix="aurora_test_file_storage_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


class MockEmbeddingService(IEmbeddingService):
    """Deterministic offline mock embedding service for unit tests."""

    def __init__(self, dimension: int = 384) -> None:
        self._dim = dimension

    def embed_text(self, text: str) -> List[float]:
        # Simple deterministic vector based on text length and ascii
        seed = sum(ord(c) for c in text) if text else 1
        np.random.seed(seed % 10000)
        vec = np.random.randn(self._dim).astype(np.float32)
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
            model_name="mock-minilm-l6-v2",
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
        return "mock-minilm-l6-v2"


def _create_sample_embedded_chunk(
    chunk_id: str,
    file_id: str = "file_1",
    text: str = "Operating systems manage hardware resources.",
    chunk_index: int = 0,
    source_page: Optional[int] = 1,
    dimension: int = 384,
    embedding: Optional[List[float]] = None,
) -> EmbeddedChunk:
    """Helper to produce a valid EmbeddedChunk for testing."""
    if embedding is None:
        vec = np.random.randn(dimension).astype(np.float32)
        norm = np.linalg.norm(vec)
        embedding = (vec / norm).tolist()

    doc_chunk = DocumentChunk(
        chunk_id=chunk_id,
        file_id=file_id,
        filename="os_notes.pdf",
        text=text,
        chunk_index=chunk_index,
        total_chunks=1,
        source_page=source_page,
        start_char=0,
        end_char=len(text),
        char_count=len(text),
        token_estimate=len(text.split()),
    )

    return EmbeddedChunk(
        chunk_id=chunk_id,
        file_id=file_id,
        embedding=embedding,
        dimension=dimension,
        chunk=doc_chunk,
    )


# =========================================================================
# Unit Tests for ChromaVectorStore
# =========================================================================

def test_store_and_retrieve_batch(temp_vector_dir):
    """Test storing a batch of embedded chunks and verifying they can be retrieved."""
    config = VectorStoreConfig(persist_dir=str(temp_vector_dir), embedding_dimension=384)
    store = ChromaVectorStore(config=config)

    chunk1 = _create_sample_embedded_chunk("c1", file_id="f1", text="Chunk one text", chunk_index=0, source_page=1)
    chunk2 = _create_sample_embedded_chunk("c2", file_id="f1", text="Chunk two text", chunk_index=1, source_page=2)

    count = store.store_embedded_chunks("conv_test", [chunk1, chunk2])
    assert count == 2
    assert store.count("conv_test") == 2

    # Retrieve single chunk
    rec1 = store.get_chunk("conv_test", "c1")
    assert rec1 is not None
    assert rec1.chunk_id == "c1"
    assert rec1.file_id == "f1"
    assert rec1.chunk.text == "Chunk one text"
    assert rec1.chunk.source_page == 1
    assert rec1.dimension == 384
    assert len(rec1.embedding) == 384


def test_persistence_across_reinitialization(temp_vector_dir):
    """Test data remains intact when ChromaVectorStore is reopened/reinitialized."""
    config = VectorStoreConfig(persist_dir=str(temp_vector_dir), embedding_dimension=384)
    store1 = ChromaVectorStore(config=config)

    chunk1 = _create_sample_embedded_chunk("c_pers_1", file_id="f_pers", text="Persisted data", source_page=4)
    store1.store_embedded_chunks("conv_pers", [chunk1])
    assert store1.count("conv_pers") == 1

    # Recreate store instance pointing to same directory
    store2 = ChromaVectorStore(config=config)
    assert store2.count("conv_pers") == 1

    rec = store2.get_chunk("conv_pers", "c_pers_1")
    assert rec is not None
    assert rec.chunk.text == "Persisted data"
    assert rec.chunk.source_page == 4


def test_conversation_isolation(temp_vector_dir):
    """Ensure vectors stored in conv_A cannot be accessed from conv_B."""
    config = VectorStoreConfig(persist_dir=str(temp_vector_dir), embedding_dimension=384)
    store = ChromaVectorStore(config=config)

    chunk_a = _create_sample_embedded_chunk("c_a", file_id="f_a", text="Secret A")
    chunk_b = _create_sample_embedded_chunk("c_b", file_id="f_b", text="Secret B")

    store.store_embedded_chunks("conv_A", [chunk_a])
    store.store_embedded_chunks("conv_B", [chunk_b])

    assert store.count("conv_A") == 1
    assert store.count("conv_B") == 1

    assert store.get_chunk("conv_A", "c_a") is not None
    assert store.get_chunk("conv_A", "c_b") is None

    assert store.get_chunk("conv_B", "c_b") is not None
    assert store.get_chunk("conv_B", "c_a") is None


def test_file_level_deletion(temp_vector_dir):
    """Ensure deleting file_1 only removes file_1 chunks and leaves file_2 intact."""
    config = VectorStoreConfig(persist_dir=str(temp_vector_dir), embedding_dimension=384)
    store = ChromaVectorStore(config=config)

    f1_c1 = _create_sample_embedded_chunk("f1_c1", file_id="file_1", text="File 1 Part 1")
    f1_c2 = _create_sample_embedded_chunk("f1_c2", file_id="file_1", text="File 1 Part 2")
    f2_c1 = _create_sample_embedded_chunk("f2_c1", file_id="file_2", text="File 2 Part 1")

    store.store_embedded_chunks("conv_multi", [f1_c1, f1_c2, f2_c1])
    assert store.count("conv_multi") == 3
    assert store.count("conv_multi", file_id="file_1") == 2
    assert store.count("conv_multi", file_id="file_2") == 1

    deleted_count = store.delete_file("conv_multi", "file_1")
    assert deleted_count == 2
    assert store.count("conv_multi") == 1
    assert store.count("conv_multi", file_id="file_1") == 0
    assert store.count("conv_multi", file_id="file_2") == 1

    assert store.get_chunk("conv_multi", "f1_c1") is None
    assert store.get_chunk("conv_multi", "f2_c1") is not None


def test_reindexing_upsert_no_duplicates(temp_vector_dir):
    """Ensure re-indexing chunks with the same chunk_id replaces rather than duplicates."""
    config = VectorStoreConfig(persist_dir=str(temp_vector_dir), embedding_dimension=384)
    store = ChromaVectorStore(config=config)

    chunk_v1 = _create_sample_embedded_chunk("chunk_fixed", file_id="f1", text="Version 1")
    store.store_embedded_chunks("conv_upsert", [chunk_v1])
    assert store.count("conv_upsert") == 1

    # Upsert with updated text
    chunk_v2 = _create_sample_embedded_chunk("chunk_fixed", file_id="f1", text="Version 2 Updated")
    store.store_embedded_chunks("conv_upsert", [chunk_v2])
    assert store.count("conv_upsert") == 1

    rec = store.get_chunk("conv_upsert", "chunk_fixed")
    assert rec.chunk.text == "Version 2 Updated"


def test_empty_batch_handling(temp_vector_dir):
    """Empty chunk lists should be handled gracefully without errors."""
    config = VectorStoreConfig(persist_dir=str(temp_vector_dir))
    store = ChromaVectorStore(config=config)

    assert store.store_embedded_chunks("conv_empty", []) == 0
    assert store.count("conv_empty") == 0


def test_dimension_mismatch_rejected(temp_vector_dir):
    """Vectors that do not match configured dimension must be rejected."""
    config = VectorStoreConfig(persist_dir=str(temp_vector_dir), embedding_dimension=384)
    store = ChromaVectorStore(config=config)

    bad_chunk = _create_sample_embedded_chunk(
        "bad_dim",
        dimension=128,
        embedding=[0.1] * 128,
    )

    with pytest.raises(VectorDimensionMismatchError, match="Vector dimension mismatch"):
        store.store_embedded_chunks("conv_bad", [bad_chunk])


def test_nan_or_infinite_vector_rejected(temp_vector_dir):
    """Vectors containing NaN or Inf must be rejected."""
    config = VectorStoreConfig(persist_dir=str(temp_vector_dir), embedding_dimension=384)
    store = ChromaVectorStore(config=config)

    nan_emb = [0.1] * 384
    nan_emb[5] = float("nan")
    nan_chunk = _create_sample_embedded_chunk("nan_c", embedding=nan_emb)

    with pytest.raises(MalformedVectorError, match="invalid float"):
        store.store_embedded_chunks("conv_nan", [nan_chunk])

    inf_emb = [0.1] * 384
    inf_emb[10] = float("inf")
    inf_chunk = _create_sample_embedded_chunk("inf_c", embedding=inf_emb)

    with pytest.raises(MalformedVectorError, match="invalid float"):
        store.store_embedded_chunks("conv_inf", [inf_chunk])


def test_empty_conversation_id_rejected(temp_vector_dir):
    """Empty or whitespace-only conversation_id must be rejected."""
    config = VectorStoreConfig(persist_dir=str(temp_vector_dir))
    store = ChromaVectorStore(config=config)
    chunk = _create_sample_embedded_chunk("c_valid")

    with pytest.raises(VectorStoreError, match="conversation_id cannot be empty"):
        store.store_embedded_chunks("", [chunk])

    with pytest.raises(VectorStoreError, match="conversation_id cannot be empty"):
        store.store_embedded_chunks("   ", [chunk])


def test_delete_conversation(temp_vector_dir):
    """Deleting a whole conversation removes the collection cleanly."""
    config = VectorStoreConfig(persist_dir=str(temp_vector_dir))
    store = ChromaVectorStore(config=config)

    c1 = _create_sample_embedded_chunk("c1", file_id="f1")
    store.store_embedded_chunks("conv_to_purge", [c1])
    assert store.count("conv_to_purge") == 1

    deleted = store.delete_conversation("conv_to_purge")
    assert deleted is True
    assert store.count("conv_to_purge") == 0


# =========================================================================
# Integration Tests with FileService
# =========================================================================

def test_file_service_end_to_end_indexing(temp_storage_dir, temp_vector_dir):
    """Verifies complete pipeline: Upload -> Extract -> Chunk -> Embed -> Store (index_file)."""
    storage_config = RuntimeStorageConfig(upload_dir=str(temp_storage_dir))
    vector_config = VectorStoreConfig(persist_dir=str(temp_vector_dir), embedding_dimension=384)

    validator = RuntimeFileValidator(storage_config)
    storage = RuntimeFileStorage(storage_config)
    chunker = RuntimeChunker()
    mock_embed = MockEmbeddingService(dimension=384)
    vector_store = ChromaVectorStore(config=vector_config)

    file_service = FileService(
        validator=validator,
        storage=storage,
        chunker=chunker,
        embedding_service=mock_embed,
        vector_store=vector_store,
    )

    # 1. Upload a text document
    content = b"# Database Indexing\nB-trees and hash indexes provide efficient logarithmic search.\n" * 5
    uploaded = file_service.upload_file(
        conversation_id="conv_pipeline",
        filename="dbms_indexing.md",
        content_type="text/markdown",
        content=content,
    )
    assert uploaded.file_id is not None

    # 2. Run index_file (executes extract -> chunk -> embed -> store)
    idx_result = file_service.index_file(
        file_id=uploaded.file_id,
        conversation_id="conv_pipeline",
        config=ChunkingConfig(chunk_size=150, chunk_overlap=20),
    )

    assert idx_result.success is True
    assert idx_result.file_id == uploaded.file_id
    assert idx_result.conversation_id == "conv_pipeline"
    assert idx_result.indexed_count > 0
    assert idx_result.dimension == 384
    assert len(idx_result.chunks) == idx_result.indexed_count

    # 3. Verify vectors exist in the vector store
    assert vector_store.count("conv_pipeline") == idx_result.indexed_count
    file_chunks = vector_store.get_file_chunks("conv_pipeline", uploaded.file_id)
    assert len(file_chunks) == idx_result.indexed_count
    assert file_chunks[0].chunk.filename == "dbms_indexing.md"

    # 4. Deleting the file through file_service must also remove the vectors
    deleted = file_service.delete_file(uploaded.file_id, "conv_pipeline")
    assert deleted is True
    assert vector_store.count("conv_pipeline", file_id=uploaded.file_id) == 0


def test_file_service_index_non_existent_file(temp_storage_dir, temp_vector_dir):
    """Attempting to index a non-existent file should raise RuntimeFileNotFoundError."""
    storage_config = RuntimeStorageConfig(upload_dir=str(temp_storage_dir))
    vector_config = VectorStoreConfig(persist_dir=str(temp_vector_dir))

    file_service = FileService(
        validator=RuntimeFileValidator(storage_config),
        storage=RuntimeFileStorage(storage_config),
        vector_store=ChromaVectorStore(config=vector_config),
    )

    with pytest.raises(RuntimeFileNotFoundError):
        file_service.index_file("file_fake_123", "conv_test")


# =========================================================================
# FastAPI Endpoint Tests: POST /v1/files/{file_id}/index
# =========================================================================

def test_api_server_index_endpoint():
    """Tests POST /v1/files/{file_id}/index on the FastAPI application."""
    client = TestClient(app)

    # 1. Upload a file
    conv_id = "test_conv_api_index"
    sample_text = "Operating systems enforce memory isolation using virtual memory paging."
    upload_res = client.post(
        "/v1/files/upload",
        data={"conversation_id": conv_id},
        files={"file": ("os_lecture.txt", sample_text.encode("utf-8"), "text/plain")},
    )
    assert upload_res.status_code == 200
    file_id = upload_res.json()["file_id"]

    try:
        # 2. Trigger indexing
        index_res = client.post(
            f"/v1/files/{file_id}/index",
            params={"conversation_id": conv_id, "chunk_size": 200, "chunk_overlap": 20},
        )
        assert index_res.status_code == 200
        data = index_res.json()
        assert data["file_id"] == file_id
        assert data["conversation_id"] == conv_id
        assert data["indexed_count"] >= 1
        assert data["dimension"] == 384
        assert data["success"] is True

        # 3. Test 404 on missing file
        missing_res = client.post("/v1/files/file_missing_999/index", params={"conversation_id": conv_id})
        assert missing_res.status_code == 404

    finally:
        # Cleanup file
        client.delete(f"/v1/files/{file_id}", params={"conversation_id": conv_id})
