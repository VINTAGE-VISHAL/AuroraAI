"""Semantic chunk model representing containerized concept learning objects."""

from typing import Any, Dict, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from aurora.models.knowledge import ConceptRelationship, KnowledgeUnit


class SemanticChunk(BaseModel):
    """Immutable semantic learning chunk containerizing units, relationships, and evidence."""
    model_config = ConfigDict(frozen=True)

    chunk_id: UUID
    concept_id: UUID
    concept_name: str
    knowledge_units: List[KnowledgeUnit] = Field(default_factory=list)
    incoming_relationships: List[ConceptRelationship] = Field(default_factory=list)
    outgoing_relationships: List[ConceptRelationship] = Field(default_factory=list)
    prerequisites: List[UUID] = Field(default_factory=list)
    evidence_ids: List[UUID] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
