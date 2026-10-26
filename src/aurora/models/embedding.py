"""Runtime vector embedding models for document retrieval and storage."""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from aurora.models.runtime_chunk import DocumentChunk


class EmbeddedChunk(BaseModel):
    """Immutable vector-embedded representation of a DocumentChunk."""
    model_config = ConfigDict(frozen=True)

    chunk_id: str = Field(description="Deterministic chunk identifier from Module 03")
    file_id: str = Field(description="Parent runtime file identifier")
    embedding: List[float] = Field(description="Normalized dense vector embedding")
    dimension: int = Field(gt=0, description="Vector dimension size, e.g. 384")
    chunk: DocumentChunk = Field(description="Full DocumentChunk containing text, offsets, and source_page")


class EmbeddingBatchResult(BaseModel):
    """Batch result detailing embedded chunks and execution statistics."""
    model_name: str
    dimension: int
    embedded_chunks: List[EmbeddedChunk]
    total_chunks: int
    normalized: bool
