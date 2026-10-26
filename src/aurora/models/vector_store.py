"""Runtime vector store models for chunk indexing, storage, and persistence."""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from aurora.models.runtime_chunk import DocumentChunk


class VectorRecord(BaseModel):
    """Clean model representing a stored vector and associated chunk metadata."""
    model_config = ConfigDict(frozen=True)

    chunk_id: str = Field(description="Deterministic chunk identifier from Module 03")
    file_id: str = Field(description="Parent runtime file identifier")
    conversation_id: str = Field(description="Conversation scope identifier")
    embedding: List[float] = Field(description="Normalized dense vector embedding")
    dimension: int = Field(gt=0, description="Vector dimension size")
    chunk: DocumentChunk = Field(description="Full DocumentChunk containing text, offsets, and source_page")


class StoredChunkSummary(BaseModel):
    """Summary of a stored chunk for index inspection and reporting."""
    chunk_id: str
    file_id: str
    filename: str
    chunk_index: int
    source_page: Optional[int] = None
    char_count: int


class IndexingResult(BaseModel):
    """Result detailing indexed vectors and execution status for a document."""
    file_id: str
    conversation_id: str
    indexed_count: int
    dimension: int
    chunks: List[StoredChunkSummary]
    success: bool = True
