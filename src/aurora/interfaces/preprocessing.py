"""Preprocessing layer contract."""

from abc import abstractmethod
from typing import List

from aurora.interfaces.base import IPipelineComponent
from aurora.models.document import ProcessedDocument, RawDocument


class IPreprocessor(IPipelineComponent[List[RawDocument], List[ProcessedDocument]]):
    """Contract for text cleaning, splitting, and mapping documents."""

    @abstractmethod
    def run(self, input_data: List[RawDocument]) -> List[ProcessedDocument]:
        """Preprocesses raw documents into cleaner, chunked structures."""
        pass
