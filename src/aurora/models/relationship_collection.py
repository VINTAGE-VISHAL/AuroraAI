"""Models for collection of concept relationships in a domain namespace."""

from typing import List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from aurora.core.artifact import ArtifactMetadata
from aurora.models.knowledge import ConceptRelationship, Evidence


class ConceptRelationshipCollection(BaseModel):
    """Immutable collection of extracted concept relationships for a domain namespace."""
    model_config = ConfigDict(frozen=True)

    collection_id: UUID
    source_document_id: str
    graph_namespace: str
    relationships: List[ConceptRelationship]
    evidences: List[Evidence] = Field(default_factory=list)
    artifact: ArtifactMetadata
