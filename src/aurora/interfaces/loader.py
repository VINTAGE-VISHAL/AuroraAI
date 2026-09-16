"""Document Loader contract definitions."""

from abc import ABC, abstractmethod

from aurora.models.document import RawDocument
from aurora.models.source import SourceDocument


class IDocumentLoader(ABC):
    """Behavioral contract for opening source document URIs and reading raw bytes."""

    @abstractmethod
    def load(self, source: SourceDocument) -> RawDocument:
        """Loads and returns the raw document model containing source bytes."""
        pass
