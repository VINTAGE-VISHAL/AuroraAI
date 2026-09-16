"""Interfaces and candidate data schemas for Relationship Extraction."""

from abc import abstractmethod
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from aurora.core.pipeline import IPipelineStep, PipelineContext
from aurora.models import (
    ConceptRelationship,
    Evidence,
    ExtractedConceptCollection,
    KnowledgeUnitCollection,
    StructuredDocument,
)


class RelationshipCandidate(BaseModel):
    """Immutable model representing a discovered relationship candidate between two concepts."""
    model_config = ConfigDict(frozen=True)

    source_concept_id: UUID
    target_concept_id: UUID
    context_segment_id: str
    context_text: str
    discovery_strategy: str
    confidence: float
    matched_span_start: Optional[int] = None
    matched_span_end: Optional[int] = None


class RelationshipPayload(BaseModel):
    """Payload carrying state between Relationship Extraction pipeline steps."""
    model_config = ConfigDict(frozen=True)

    concepts: ExtractedConceptCollection
    units: KnowledgeUnitCollection
    document: StructuredDocument
    graph_namespace: str
    candidates: List[RelationshipCandidate] = Field(default_factory=list)
    relationships: List[ConceptRelationship] = Field(default_factory=list)
    evidences: List[Evidence] = Field(default_factory=list)


class IRelationshipStep(IPipelineStep[RelationshipPayload, RelationshipPayload]):
    """Abstract contract for steps in the Relationship Extraction pipeline."""

    @abstractmethod
    def process(
        self, input_data: RelationshipPayload, context: PipelineContext
    ) -> RelationshipPayload:
        """Processes and enriches the relationship extraction payload."""
        pass
