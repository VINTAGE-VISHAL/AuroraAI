"""Artifact metadata and source tracking models defining boundary schemas."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ArtifactMetadata(BaseModel):
    """Immutable metadata tracking schema lineage and checksum properties."""
    model_config = ConfigDict(frozen=True)

    artifact_id: UUID
    parent_artifact_ids: List[UUID] = Field(default_factory=list)
    derived_from: List[UUID] = Field(default_factory=list)
    checksum: str
    created_at: datetime
    schema_version: str = "1.0.0"


class SourceReference(BaseModel):
    """Immutable schema tracking source origin location maps."""
    model_config = ConfigDict(frozen=True)

    source_uri: str
    page_number: Optional[int] = None
    start_offset: Optional[int] = None
    end_offset: Optional[int] = None
    segment_id: Optional[str] = None
