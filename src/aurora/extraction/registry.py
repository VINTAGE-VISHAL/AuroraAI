"""Registry managing dynamic registration of Document Extractor factories."""

from typing import Dict, Type

from aurora.core.exceptions import RegistryError, UnsupportedExtractionError
from aurora.extraction.interfaces import IDocumentExtractor
from aurora.extraction.models import DocumentType


class ExtractorRegistry:
    """Manages maps of DocumentTypes to concrete Extractor plugin classes."""

    _registry: Dict[DocumentType, Type[IDocumentExtractor]] = {}

    @classmethod
    def register(cls, doc_type: DocumentType, extractor_cls: Type[IDocumentExtractor]) -> None:
        """Register an extractor class factory. Raises RegistryError on duplicate."""
        if doc_type in cls._registry:
            raise RegistryError(f"An extractor is already registered for type: {doc_type}")
        cls._registry[doc_type] = extractor_cls

    @classmethod
    def get_extractor_class(cls, doc_type: DocumentType) -> Type[IDocumentExtractor]:
        """Lookup registered extractor factory. Raises UnsupportedExtractionError if missing."""
        if doc_type not in cls._registry:
            raise UnsupportedExtractionError(f"No extractor plugin registered for type: {doc_type}")
        return cls._registry[doc_type]

    @classmethod
    def clear(cls) -> None:
        """Reset registry contents for clean test setups."""
        cls._registry.clear()
