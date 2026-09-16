"""Interfaces for document normalization steps."""

from abc import abstractmethod

from aurora.core.pipeline import IPipelineStep, PipelineContext


class INormalizationStep(IPipelineStep[str, str]):
    """Behavioral contract for text normalization pipeline steps."""

    @abstractmethod
    def process(self, input_data: str, context: PipelineContext) -> str:
        """Applies normalization formatting to the input string."""
        pass
