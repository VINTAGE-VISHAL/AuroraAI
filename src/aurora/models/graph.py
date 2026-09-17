"""Models for representing the assembled knowledge graph."""

from typing import Dict
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from aurora.core.artifact import ArtifactMetadata
from aurora.models.knowledge import Concept, ConceptRelationship, KnowledgeUnit
from aurora.models.unit_collection import ConceptKnowledgeMapping


class GraphStatistics(BaseModel):
    """Immutable computed quality and topological metrics of a KnowledgeGraph."""
    model_config = ConfigDict(frozen=True)

    concept_count: int
    relationship_count: int
    knowledge_unit_count: int
    edge_density: float
    connected_components: int
    cycles_detected: int
    orphan_concepts: int


class KnowledgeGraph(BaseModel):
    """Immutable assembled graph mapping concepts, units, and relationships."""
    model_config = ConfigDict(frozen=True)

    graph_id: UUID
    namespace: str
    graph_version: str = "1.0.0"
    ontology_version: str = "1.0.0"
    taxonomy_version: str = "1.0.0"
    pipeline_version: str = "1.0.0"

    # Indexed dict structures for O(1) traversal and referencing
    concepts: Dict[UUID, Concept]
    knowledge_units: Dict[UUID, KnowledgeUnit]
    relationships: Dict[UUID, ConceptRelationship]
    mappings: Dict[UUID, ConceptKnowledgeMapping]

    statistics: GraphStatistics
    artifact: ArtifactMetadata
