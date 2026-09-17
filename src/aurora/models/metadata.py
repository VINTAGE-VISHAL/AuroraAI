"""Metadata schemas for files and ingested resources."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class FileMetadata(BaseModel):
    """Metadata detailing source origins, parsing details, and custom metadata."""
    source_path: str
    file_type: str
    char_count: int
    custom_metadata: Dict[str, Any] = Field(default_factory=dict)
    author: Optional[str] = None
    created_at: Optional[str] = None
