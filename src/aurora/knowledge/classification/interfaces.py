"""Interfaces for the Knowledge Unit Classification subsystem."""

from abc import abstractmethod
from typing import Dict, List

from pydantic import BaseModel, ConfigDict, Field

from aurora.core.pipeline import IPipelineStep, PipelineContext
from aurora.models import (
    ConceptKnowledgeMapping,
    ConceptOccurrence,
    DocumentSegment,
    Evidence,
    ExtractedConceptCollection,
    KnowledgeType,
    KnowledgeUnit,
    StructuredDocument,
)


class ClassificationPayload(BaseModel):
    """Payload carrying state between Knowledge Unit classification steps."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    concepts: ExtractedConceptCollection
    document: StructuredDocument
    candidate_segments: List[DocumentSegment] = Field(default_factory=list)
    classified_types: Dict[str, KnowledgeType] = Field(default_factory=dict)
    units: List[KnowledgeUnit] = Field(default_factory=list)
    occurrences: List[ConceptOccurrence] = Field(default_factory=list)
    evidences: List[Evidence] = Field(default_factory=list)
    mappings: List[ConceptKnowledgeMapping] = Field(default_factory=list)


class IClassificationStep(IPipelineStep[ClassificationPayload, ClassificationPayload]):
    """Abstract contract for individual steps in the Classification pipeline."""

    @abstractmethod
    def process(
        self, input_data: ClassificationPayload, context: PipelineContext
    ) -> ClassificationPayload:
        """Processes and enriches the classification payload."""
        pass
