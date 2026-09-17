"""Models for classified knowledge units and their associations to concepts."""

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from aurora.core.artifact import ArtifactMetadata
from aurora.models.knowledge import ConceptOccurrence, Evidence, KnowledgeUnit


class ConceptKnowledgeMapping(BaseModel):
    """Immutable model mapping a concept to its classifying knowledge units."""
    model_config = ConfigDict(frozen=True)

    concept_id: UUID
    knowledge_unit_ids: List[UUID]
    primary_unit: Optional[UUID] = None
    confidence: float = 1.0


class KnowledgeUnitCollection(BaseModel):
    """Immutable collection bundling units, mappings, occurrences, and evidence."""
    model_config = ConfigDict(frozen=True)

    collection_id: UUID
    source_document_id: str
    units: List[KnowledgeUnit]
    mappings: List[ConceptKnowledgeMapping]
    occurrences: List[ConceptOccurrence] = Field(default_factory=list)
    evidences: List[Evidence] = Field(default_factory=list)
    artifact: ArtifactMetadata
