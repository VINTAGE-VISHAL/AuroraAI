"""Runtime semantic retrieval models."""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from aurora.models.runtime_chunk import DocumentChunk


class ScoredChunk(BaseModel):
    """Immutable retrieved chunk paired with relevance score and attribution metadata."""
    model_config = ConfigDict(frozen=True)

    chunk_id: str = Field(description="Deterministic chunk identifier from Module 03")
    file_id: str = Field(description="Parent runtime file identifier")
    conversation_id: str = Field(description="Conversation isolation scope")
    score: float = Field(description="Calculated cosine similarity score (higher = more relevant, range: [-1.0, 1.0] or [0.0, 1.0])")
    distance: float = Field(description="Raw distance returned by vector database (lower = closer)")
    chunk: DocumentChunk = Field(description="Complete DocumentChunk with text, offsets, and source_page")


class RetrievalResult(BaseModel):
    """Response returned by the semantic retriever."""
    query: str
    conversation_id: str
    file_id: Optional[str] = None
    top_k: int
    total_retrieved: int
    results: List[ScoredChunk]
