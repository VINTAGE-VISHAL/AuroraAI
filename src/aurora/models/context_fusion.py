"""Models for RAG context fusion, source attribution, and prompt assembly."""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SourceReference(BaseModel):
    """Clean attribution reference for a chunk included in the fused context."""
    model_config = ConfigDict(frozen=True)

    chunk_id: str = Field(description="Unique deterministic chunk ID")
    file_id: str = Field(description="Parent file ID")
    filename: str = Field(description="Original sanitized filename")
    source_page: Optional[int] = Field(default=None, description="1-indexed source PDF page number if known")
    chunk_index: int = Field(description="0-indexed position of chunk in the document")
    char_count: int = Field(description="Character length of chunk text")
    token_estimate: int = Field(description="Estimated token length of chunk")
    relevance_score: float = Field(description="Cosine similarity score (higher = more relevant)")
    label: str = Field(description="Human-readable citation label, e.g. [Source 1]")


class ExcludedChunk(BaseModel):
    """Details of a chunk excluded from context due to budget or deduplication."""
    model_config = ConfigDict(frozen=True)

    chunk_id: str
    file_id: str
    filename: str
    reason: str  # "budget_exceeded", "duplicate_content", "oversized"
    token_estimate: int
    relevance_score: float


class FusedContext(BaseModel):
    """Bounded, structured context ready for LLM prompt insertion alongside source metadata."""
    query: str
    conversation_id: str
    context_text: str = Field(description="Structured reference text with source markers and grounding boundaries")
    sources: List[SourceReference] = Field(description="Attribution metadata for all included chunks for Module 11 citations")
    included_chunks_count: int
    excluded_chunks: List[ExcludedChunk] = Field(default_factory=list)
    max_token_budget: int
    estimated_tokens_used: int
    has_context: bool


class GroundedPrompt(BaseModel):
    """Complete assembled prompt structure separating system guidelines, untrusted context, and user query."""
    system_prompt: str
    user_query: str
    context: FusedContext
    assembled_prompt: str = Field(description="Full formatted prompt ready for LLM consumption")
