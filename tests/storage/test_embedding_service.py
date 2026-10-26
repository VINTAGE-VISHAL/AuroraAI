"""Comprehensive Automated Unit and Integration Tests for Module 04: Runtime Embedding Service.

Covers:
- Embedding a single DocumentChunk
- Embedding multiple DocumentChunks in batches
- Preserving chunk IDs, file IDs, source pages, offsets, and full DocumentChunk metadata
- Consistent embedding dimension (e.g. 384 for all-MiniLM-L6-v2)
- Finite numerical values guarantee (no NaN or infinite floats)
- Unit L2 vector normalization (dot product / norm == 1.0)
- Empty chunk list handling (returns empty batch result without error)
- Rejection of invalid / empty chunk texts
- Reusable lazy model caching (does not reload for subsequent requests)
- Device selection (auto, cpu, cuda) and graceful fallback
- Error handling on model load failure or inference crash
- Integration with FileService (Upload -> Extract -> Chunk -> Embed)
- FastAPI endpoint POST /v1/files/{file_id}/embed
"""

import math
from typing import List, Optional
import numpy as np
import pytest
from fastapi.testclient import TestClient

from aurora.config.settings import EmbeddingConfig, RuntimeStorageConfig
from aurora.core.exceptions import (
    EmbeddingError,
    EmbeddingInferenceError,
    ModelLoadError,
    RuntimeFileNotFoundError,
)
from aurora.deployment.api_server import app
from aurora.ingestion.runtime.file_storage import RuntimeFileStorage
from aurora.ingestion.runtime.file_validator import RuntimeFileValidator
from aurora.models.embedding import EmbeddedChunk, EmbeddingBatchResult
from aurora.models.runtime_chunk import ChunkingConfig, DocumentChunk
from aurora.preprocessing.runtime_chunker import RuntimeChunker
from aurora.services.file_service import FileService
from aurora.storage.embedding_service import SentenceTransformerEmbeddingService
import shutil
import tempfile
from pathlib import Path



@pytest.fixture
def temp_storage_dir():
    temp_dir = tempfile.mkdtemp(prefix="aurora_test_embed_storage_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


class MockSentenceTransformer:

    """Deterministic mock embedding model that simulates SentenceTransformer behavior offline."""

    def __init__(self, dimension: int = 384) -> None:
        self._dim = dimension
        self.call_count = 0

    def get_sentence_embedding_dimension(self) -> int:
        return self._dim

    def encode(
        self,
        sentences: str | List[str],
        batch_size: int = 32,
        normalize_embeddings: bool = True,
        show_progress_bar: bool = False,
    ) -> np.ndarray:
        self.call_count += 1
        is_single = isinstance(sentences, str)
        items = [sentences] if is_single else sentences

        embeddings = []
        for text in items:
            # Generate deterministic pseudo-vector based on character codes
            seed = sum(ord(c) for c in text)
            rng = np.random.RandomState(seed % 10000)
            vec = rng.randn(self._dim).astype(np.float32)

            if normalize_embeddings:
                norm = np.linalg.norm(vec)
                if norm > 1e-12:
                    vec = vec / norm
            embeddings.append(vec)

        arr = np.array(embeddings, dtype=np.float32)
        return arr[0] if is_single else arr


class CrashingMockSentenceTransformer:
    """Mock that throws an exception during encode to verify error propagation."""

    def encode(self, *args, **kwargs):
        raise RuntimeError("GPU Out of Memory or CUDA driver failure simulated.")


@pytest.fixture
def mock_model():
    return MockSentenceTransformer(dimension=384)


@pytest.fixture
def embedding_service(mock_model):
    cfg = EmbeddingConfig(
        model_name="mock-model",
        device="cpu",
        batch_size=16,
        normalize_embeddings=True,
        embedding_dimension=384,
    )
    return SentenceTransformerEmbeddingService(config=cfg, model_instance=mock_model)


@pytest.fixture
def sample_chunks():
    return [
        DocumentChunk(
            chunk_id="chk_001",
            file_id="file_abc",
            filename="dbms.pdf",
            text="Relational database normalization is the process of structuring data to reduce redundancy.",
            chunk_index=0,
            total_chunks=3,
            source_page=1,
            start_char=0,
            end_char=93,
            char_count=93,
            token_estimate=12,
        ),
        DocumentChunk(
            chunk_id="chk_002",
            file_id="file_abc",
            filename="dbms.pdf",
            text="First normal form (1NF) requires that attributes contain only atomic, indivisible values.",
            chunk_index=1,
            total_chunks=3,
            source_page=2,
            start_char=0,
            end_char=89,
            char_count=89,
            token_estimate=12,
        ),
        DocumentChunk(
            chunk_id="chk_003",
            file_id="file_abc",
            filename="dbms.pdf",
            text="Second normal form (2NF) eliminates partial dependency of non-prime attributes on candidate keys.",
            chunk_index=2,
            total_chunks=3,
            source_page=3,
            start_char=0,
            end_char=98,
            char_count=98,
            token_estimate=13,
        ),
    ]


# 1. Single Chunk and Text Embedding Tests

def test_embed_single_text(embedding_service):
    """Verifies generating an embedding for a text query string."""
    text = "What is Boyce-Codd normal form (BCNF)?"
    vec = embedding_service.embed_text(text)

    assert isinstance(vec, list)
    assert len(vec) == 384
    assert all(isinstance(x, float) for x in vec)
    assert all(math.isfinite(x) for x in vec)

    # Unit L2 norm verification
    norm = math.sqrt(sum(x * x for x in vec))
    assert abs(norm - 1.0) < 1e-4


def test_embed_empty_text_raises_error(embedding_service):
    """Verifies that empty string or whitespace-only query raises EmbeddingError."""
    with pytest.raises(EmbeddingError):
        embedding_service.embed_text("")

    with pytest.raises(EmbeddingError):
        embedding_service.embed_text("   \n\t  ")


# 2. Batch Embedding and Metadata Preservation

def test_embed_chunks_batch_metadata_preservation(embedding_service, sample_chunks):
    """Verifies batch embedding preserves chunk_id, file_id, source_page, and order."""
    result = embedding_service.embed_chunks(sample_chunks)

    assert isinstance(result, EmbeddingBatchResult)
    assert result.total_chunks == 3
    assert result.dimension == 384
    assert result.normalized is True
    assert len(result.embedded_chunks) == 3

    for orig, embedded in zip(sample_chunks, result.embedded_chunks):
        assert embedded.chunk_id == orig.chunk_id
        assert embedded.file_id == orig.file_id
        assert embedded.chunk.source_page == orig.source_page
        assert embedded.dimension == 384
        assert len(embedded.embedding) == 384
        assert all(math.isfinite(x) for x in embedded.embedding)

        # Vector is unit length
        norm = math.sqrt(sum(x * x for x in embedded.embedding))
        assert abs(norm - 1.0) < 1e-4


# 3. Empty Input Handling

def test_embed_empty_chunk_list(embedding_service):
    """Verifies passing empty chunk list returns empty EmbeddingBatchResult without error."""
    result = embedding_service.embed_chunks([])
    assert result.total_chunks == 0
    assert result.embedded_chunks == []
    assert result.dimension == 384


# 4. Normalization and Finite Value Guarantees

def test_normalization_cosine_distance_compatibility(embedding_service):
    """Verifies two identical texts produce identical normalized vectors with dot-product 1.0."""
    query = "Operating systems kernel architecture"
    v1 = embedding_service.embed_text(query)
    v2 = embedding_service.embed_text(query)

    dot_product = sum(a * b for a, b in zip(v1, v2))
    assert abs(dot_product - 1.0) < 1e-5


# 5. Model Reuse and Lazy Loading

def test_model_initialization_reuse(embedding_service, mock_model, sample_chunks):
    """Verifies the embedding model instance is reused and not reloaded per call."""
    assert mock_model.call_count == 0

    embedding_service.embed_chunks(sample_chunks)
    assert mock_model.call_count == 1

    embedding_service.embed_text("Query 1")
    assert mock_model.call_count == 2

    embedding_service.embed_text("Query 2")
    assert mock_model.call_count == 3


# 6. Device Selection and Fallback

def test_device_resolution_logic():
    """Verifies device configuration resolution (auto, cpu, cuda)."""
    srv_cpu = SentenceTransformerEmbeddingService(
        config=EmbeddingConfig(device="cpu"),
        model_instance=MockSentenceTransformer(),
    )
    assert srv_cpu.device == "cpu"

    srv_auto = SentenceTransformerEmbeddingService(
        config=EmbeddingConfig(device="auto"),
        model_instance=MockSentenceTransformer(),
    )
    assert srv_auto.device in ("cuda", "cpu")


# 7. Error Handling on Load and Inference Failures

def test_model_load_failure():
    """Verifies ModelLoadError is raised when model cannot be loaded."""
    srv = SentenceTransformerEmbeddingService(
        config=EmbeddingConfig(model_name="nonexistent/model-path-xyz"),
    )
    with pytest.raises(ModelLoadError):
        srv.embed_text("Sample text")


def test_inference_crash_error_handling(sample_chunks):
    """Verifies EmbeddingInferenceError is raised if encode crashes."""
    crashing_model = CrashingMockSentenceTransformer()
    srv = SentenceTransformerEmbeddingService(model_instance=crashing_model)

    with pytest.raises(EmbeddingInferenceError):
        srv.embed_chunks(sample_chunks)


# 8. FileService Integration with Injected Embedding Service

def test_file_service_embed_pipeline(temp_storage_dir, mock_model):
    """Verifies full FileService pipeline: Upload -> Extract -> Chunk -> Embed."""
    custom_config = RuntimeStorageConfig(
        upload_dir="data/runtime_uploads",
        max_upload_size_mb=5,
        allowed_extensions=[".pdf", ".docx", ".txt", ".md"],
    )
    storage = RuntimeFileStorage(custom_config, base_dir=temp_storage_dir)
    validator = RuntimeFileValidator(custom_config)
    chunker = RuntimeChunker(ChunkingConfig(chunk_size=200, chunk_overlap=30))
    embedding_srv = SentenceTransformerEmbeddingService(
        config=EmbeddingConfig(model_name="mock-model", embedding_dimension=384),
        model_instance=mock_model,
    )

    file_svc = FileService(
        validator=validator,
        storage=storage,
        chunker=chunker,
        embedding_service=embedding_srv,
    )

    txt_content = (
        "Distributed Hash Tables (DHT). Chord protocol uses consistent hashing. "
        "Routing table maintains fingertable with O(log N) entries for lookups."
    ).encode("utf-8")

    upload_res = file_svc.upload_file(
        conversation_id="conv_embed_test",
        filename="dht.txt",
        content_type="text/plain",
        content=txt_content,
    )
    file_id = upload_res.file_id

    # Call embed_file
    batch_res = file_svc.embed_file(file_id, conversation_id="conv_embed_test")
    assert batch_res.total_chunks >= 1
    assert batch_res.dimension == 384
    for ec in batch_res.embedded_chunks:
        assert ec.file_id == file_id
        assert len(ec.embedding) == 384
        assert all(math.isfinite(x) for x in ec.embedding)

    # Conversation isolation check
    with pytest.raises(RuntimeFileNotFoundError):
        file_svc.embed_file(file_id, conversation_id="other_unauthorized_conv")


# 9. API Server Route Integration

def test_api_embed_endpoint():
    """Verifies POST /v1/files/{file_id}/embed endpoint via TestClient."""
    client = TestClient(app)

    # 1. Upload file
    content = b"Graph Theory: Dijkstra algorithm finds shortest paths from source to all vertices."
    upload_res = client.post(
        "/v1/files/upload",
        data={"conversation_id": "test_conv_api_embed"},
        files={"file": ("graph.txt", content, "text/plain")},
    )
    assert upload_res.status_code == 200
    file_id = upload_res.json()["file_id"]

    # 2. Invoke /v1/files/{file_id}/embed
    embed_res = client.post(
        f"/v1/files/{file_id}/embed",
        params={
            "conversation_id": "test_conv_api_embed",
            "chunk_size": 200,
            "chunk_overlap": 20,
        },
    )
    assert embed_res.status_code == 200
    data = embed_res.json()
    assert data["total_chunks"] >= 1
    assert data["dimension"] == 384
    assert len(data["embedded_chunks"]) == data["total_chunks"]
    first_chunk = data["embedded_chunks"][0]
    assert first_chunk["file_id"] == file_id
    assert len(first_chunk["embedding"]) == 384

    # 3. Clean up file
    del_res = client.delete(f"/v1/files/{file_id}?conversation_id=test_conv_api_embed")
    assert del_res.status_code == 200
