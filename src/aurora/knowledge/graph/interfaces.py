"""Interfaces and payload structures for the Knowledge Graph Builder pipeline."""

from abc import abstractmethod
from typing import Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from aurora.core.pipeline import IPipelineStep, PipelineContext
from aurora.models import (
    Concept,
    ConceptKnowledgeMapping,
    ConceptRelationship,
    ConceptRelationshipCollection,
    ExtractedConceptCollection,
    GraphStatistics,
    KnowledgeUnit,
    KnowledgeUnitCollection,
)


class GraphPayload(BaseModel):
    """Payload carrying state between Knowledge Graph assembly and validation steps."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    concepts: ExtractedConceptCollection
    units: KnowledgeUnitCollection
    relationships: ConceptRelationshipCollection

    indexed_concepts: Dict[UUID, Concept] = Field(default_factory=dict)
    indexed_units: Dict[UUID, KnowledgeUnit] = Field(default_factory=dict)
    indexed_relationships: Dict[UUID, ConceptRelationship] = Field(default_factory=dict)
    indexed_mappings: Dict[UUID, ConceptKnowledgeMapping] = Field(default_factory=dict)

    statistics: Optional[GraphStatistics] = None


class IGraphStep(IPipelineStep[GraphPayload, GraphPayload]):
    """Abstract contract for steps in the Knowledge Graph Builder pipeline."""

    @abstractmethod
    def process(
        self, input_data: GraphPayload, context: PipelineContext
    ) -> GraphPayload:
        """Processes and enriches the graph assembly payload."""
        pass
