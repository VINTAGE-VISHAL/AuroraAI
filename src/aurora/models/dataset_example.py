"""Models defining individual dataset training examples and traceable mappings."""

from typing import Any, Dict, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DatasetExampleTraceability(BaseModel):
    """Lineage container pointing back to the exact source items that generated this example."""
    model_config = ConfigDict(frozen=True)

    knowledge_unit_ids: List[UUID] = Field(default_factory=list)
    concept_ids: List[UUID] = Field(default_factory=list)
    relationship_ids: List[UUID] = Field(default_factory=list)
    evidence_ids: List[UUID] = Field(default_factory=list)
    chunk_ids: List[UUID] = Field(default_factory=list)


class DatasetExample(BaseModel):
    """Immutable model representing a single formatted instruction tuning example."""
    model_config = ConfigDict(frozen=True)

    example_id: UUID
    format_tag: str  # e.g., "tutor", "mcq", "flashcard", "coding"
    input: str
    output: str
    supporting_context: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    traceability: DatasetExampleTraceability


class DatasetCollection(BaseModel):
    """Immutable collection bundling a list of dataset examples."""
    model_config = ConfigDict(frozen=True)

    collection_id: UUID
    examples: List[DatasetExample]
    metadata: Dict[str, Any] = Field(default_factory=dict)
