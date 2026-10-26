"""Runtime chunk models for document preprocessing and vector retrieval."""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator
from aurora.core.exceptions import InvalidChunkingConfigError



class DocumentChunk(BaseModel):
    """Immutable runtime text chunk suitable for embedding and retrieval."""
    model_config = ConfigDict(frozen=True)

    chunk_id: str = Field(description="Deterministic unique chunk identifier")
    file_id: str = Field(description="Parent runtime file identifier")
    filename: str = Field(description="Original sanitized filename")
    text: str = Field(description="Normalized non-empty chunk text")
    chunk_index: int = Field(ge=0, description="0-indexed position within the document chunk sequence")
    total_chunks: int = Field(ge=1, description="Total count of chunks generated for the document")
    source_page: Optional[int] = Field(default=None, description="1-indexed source PDF page number if known")
    start_char: Optional[int] = Field(default=None, description="Character offset start in the source document/page")
    end_char: Optional[int] = Field(default=None, description="Character offset end in the source document/page")
    char_count: int = Field(ge=0, description="Character length of this chunk text")
    token_estimate: int = Field(ge=0, description="Approximate word/token count for budget estimations")


class ChunkingConfig(BaseModel):

    """Configuration settings for runtime document chunking."""
    chunk_size: int = 500
    chunk_overlap: int = 50
    min_chunk_size: int = 20

    @model_validator(mode="after")
    def validate_chunk_settings(self) -> "ChunkingConfig":
        if self.chunk_size <= 0:
            raise InvalidChunkingConfigError(f"chunk_size must be positive, got {self.chunk_size}")
        if self.chunk_overlap < 0:
            raise InvalidChunkingConfigError(f"chunk_overlap cannot be negative, got {self.chunk_overlap}")
        if self.chunk_overlap >= self.chunk_size:
            raise InvalidChunkingConfigError(
                f"chunk_overlap ({self.chunk_overlap}) must be strictly less than chunk_size ({self.chunk_size})"
            )
        if self.min_chunk_size <= 0:
            raise InvalidChunkingConfigError(f"min_chunk_size must be positive, got {self.min_chunk_size}")
        if self.min_chunk_size > self.chunk_size:
            raise InvalidChunkingConfigError(
                f"min_chunk_size ({self.min_chunk_size}) cannot exceed chunk_size ({self.chunk_size})"
            )
        return self



class ChunkingResult(BaseModel):
    """Response returned by the runtime chunking service."""
    file_id: str
    filename: str
    chunks: List[DocumentChunk]
    total_chunks: int
    total_characters: int
    has_content: bool
