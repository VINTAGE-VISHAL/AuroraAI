"""DOCX document extractor plugin stub."""

from aurora.core.exceptions import UnsupportedExtractionError
from aurora.extraction.interfaces import IDocumentExtractor
from aurora.extraction.models import (
    DocumentType,
    ExtractedDocument,
    ExtractorCapability,
    ExtractorMetadata,
)
from aurora.models.document import RawDocument


class DOCXExtractor(IDocumentExtractor):
    """Stub DOCX extractor to be fully implemented in future milestones."""

    def extract(self, doc: RawDocument) -> ExtractedDocument:
        raise UnsupportedExtractionError("DOCX parsing is not yet implemented.")

    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            supported_type=DocumentType.DOCX,
            version="0.1.0",
            capabilities={ExtractorCapability.TEXT},
        )
