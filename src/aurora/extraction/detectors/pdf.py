"""PDF format signature detector."""

from typing import Optional

from aurora.core.pipeline import PipelineContext
from aurora.extraction.interfaces import IDocumentDetector
from aurora.extraction.models import DetectionMethod, DocumentDescriptor, DocumentType


class PDFDetector(IDocumentDetector):
    """Detects PDF magic signature `%PDF-`."""

    def process(self, input_data: bytes, context: PipelineContext) -> Optional[DocumentDescriptor]:
        if input_data.startswith(b"%PDF-"):
            return DocumentDescriptor(
                doc_type=DocumentType.PDF,
                confidence=1.0,
                method=DetectionMethod.MAGIC_BYTES,
                signature="%PDF-",
            )
        return None
