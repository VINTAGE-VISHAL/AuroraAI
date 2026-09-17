"""Collection models bundling extracted concept lists."""

from typing import List
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from aurora.core.artifact import ArtifactMetadata
from aurora.models.knowledge import Concept


class ExtractedConceptCollection(BaseModel):
    """Immutable collection bundling concepts extracted from a single source document."""
    model_config = ConfigDict(frozen=True)

    collection_id: UUID
    source_document_id: str
    concepts: List[Concept]
    taxonomy_version: str
    pipeline_version: str
    artifact: ArtifactMetadata
