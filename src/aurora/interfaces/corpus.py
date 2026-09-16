"""Interface contracts for Phase C - Lossless Training Corpus components."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from aurora.interfaces.base import IPipelineComponent
from aurora.models.document import StructuredDocument
from aurora.models.training_corpus import TrainingCorpus


class ILosslessCorpusBuilder(ABC):
    """Contract for converting StructuredDocuments into a TrainingCorpus without altering knowledge."""

    @abstractmethod
    def build(self, documents: List[StructuredDocument]) -> TrainingCorpus:
        """Convert structured documents to a domain-specific TrainingCorpus."""
        pass


from aurora.models.training_corpus import CorpusValidationResult, TrainingCorpus


class ICorpusValidator(ABC):
    """Contract for verifying the completeness, ordering, duplication, and traceability of the corpus."""

    @abstractmethod
    def validate(
        self, corpus: TrainingCorpus
    ) -> CorpusValidationResult:
        """Perform validation checks on the corpus itself.

        Raises:
            InterfaceError: If any validation invariant is violated.
        """
        pass


from aurora.models.training_corpus import SerializedCorpus


class ITrainingSerializer(ABC):
    """Contract for serializing a TrainingCorpus into a training format representation."""

    @abstractmethod
    def serialize(self, corpus: TrainingCorpus) -> SerializedCorpus:
        """Serialize corpus documents into training-format-compatible payloads."""
        pass


from aurora.models.training_corpus import ExportResult, SerializedCorpus


class ICorpusExporter(ABC):
    """Contract for writing serialized training data to files."""

    @abstractmethod
    def export(self, serialized_corpus: SerializedCorpus, output_path: str) -> ExportResult:
        """Export serialized training data to a physical storage destination."""
        pass


from aurora.models.training_corpus import CorpusPipelineResult


class ICorpusPipeline(IPipelineComponent[List[StructuredDocument], CorpusPipelineResult], ABC):
    """Contract for the end-to-end corpus building pipeline."""
    pass
