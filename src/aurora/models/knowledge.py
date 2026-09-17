"""Knowledge layer models defining concept taxonomy and knowledge structures."""

from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from aurora.core.artifact import ArtifactMetadata


class KnowledgeType(str, Enum):
    """Educational content roles for classified segments."""
    DEFINITION = "DEFINITION"
    ALGORITHM = "ALGORITHM"
    EXAMPLE = "EXAMPLE"
    FORMULA = "FORMULA"
    EXERCISE = "EXERCISE"
    PROOF = "PROOF"
    THEOREM = "THEOREM"
    NOTE = "NOTE"
    WARNING = "WARNING"


class KnowledgeUnit(BaseModel):
    """Immutable educational content block tied to a specific Concept."""
    model_config = ConfigDict(frozen=True)

    unit_id: UUID
    type: KnowledgeType
    title: Optional[str] = None
    content: str
    occurrence_ids: List[UUID] = Field(default_factory=list)
    evidence_ids: List[UUID] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)



class Concept(BaseModel):
    """A canonical domain concept with aliases and associated KnowledgeUnits."""
    model_config = ConfigDict(frozen=True)

    concept_id: UUID
    canonical_name: str
    aliases: List[str] = Field(default_factory=list)
    subject: str
    difficulty: str
    knowledge_units: List[KnowledgeUnit] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConceptTaxonomy(BaseModel):
    """Immutable concept taxonomy grouping curated educational concepts."""
    model_config = ConfigDict(frozen=True)

    taxonomy_id: UUID
    name: str
    concepts: List[Concept]
    artifact: ArtifactMetadata


class RelationshipType(str, Enum):
    """Ontology relationship types mapping concept connectivity."""
    PREREQUISITE_OF = "PREREQUISITE_OF"
    PART_OF = "PART_OF"
    DEPENDS_ON = "DEPENDS_ON"
    RELATED_TO = "RELATED_TO"
    SUBTYPE_OF = "SUBTYPE_OF"
    REFERENCES = "REFERENCES"


class ConceptRelationship(BaseModel):
    """Immutable relationship link connecting two Concept entities."""
    model_config = ConfigDict(frozen=True)

    relationship_id: UUID
    source_concept_id: UUID
    target_concept_id: UUID
    type: RelationshipType
    confidence: float = 1.0
    discovery_strategy: str = "RuleBased"
    created_by_pipeline: str = "RelationshipPipeline"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConceptOccurrence(BaseModel):
    """Immutable record tracking where a concept was mentioned in the source document."""
    model_config = ConfigDict(frozen=True)

    occurrence_id: UUID
    concept_id: UUID
    segment_id: str
    page_number: Optional[int] = None
    confidence: float
    matched_text: str
    strategy: str
    occurrence_order: int


class Evidence(BaseModel):
    """Immutable generic evidence record explaining why any knowledge item exists."""
    model_config = ConfigDict(frozen=True)

    evidence_id: UUID
    target_type: str  # Concept, Relationship, KnowledgeUnit
    target_id: UUID
    segment_id: str
    page_number: Optional[int] = None
    matched_text: str
    matched_span_start: Optional[int] = None
    matched_span_end: Optional[int] = None
    strategy: str
    confidence: float


