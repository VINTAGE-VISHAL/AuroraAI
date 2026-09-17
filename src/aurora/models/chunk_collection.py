"""Models for collection of assembled semantic learning chunks."""

from typing import List
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from aurora.core.artifact import ArtifactMetadata
from aurora.models.chunk import SemanticChunk


class SemanticChunkCollection(BaseModel):
    """Immutable collection bundling all generated semantic chunks from a domain graph."""
    model_config = ConfigDict(frozen=True)

    collection_id: UUID
    chunks: List[SemanticChunk]
    artifact: ArtifactMetadata
