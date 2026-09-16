"""Interfaces for Document Extractor plugins."""

from abc import ABC, abstractmethod
from typing import Optional

from aurora.core.pipeline import IPipelineStep, PipelineContext
from aurora.extraction.models import DocumentDescriptor, ExtractedDocument, ExtractorMetadata
from aurora.models.document import RawDocument


class IDocumentDetector(IPipelineStep[bytes, Optional[DocumentDescriptor]]):
    """Behavioral contract for format-specific signature classification detectors."""

    @abstractmethod
    def process(self, input_data: bytes, context: PipelineContext) -> Optional[DocumentDescriptor]:
        """Inspects raw bytes to classify the format signature. Returns None if unmatched."""
        pass


class IDocumentExtractor(ABC):
    """Behavioral contract for format-specific document parsing plugins."""

    @abstractmethod
    def extract(self, doc: RawDocument) -> ExtractedDocument:
        """Parses RawDocument bytes and returns extracted text structures."""
        pass

    @abstractmethod
    def get_metadata(self) -> ExtractorMetadata:
        """Returns capabilities and format parameters of this extractor plugin."""
        pass
