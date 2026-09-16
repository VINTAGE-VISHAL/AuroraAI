"""HTML format signature detector."""

from typing import Optional

from aurora.core.pipeline import PipelineContext
from aurora.extraction.interfaces import IDocumentDetector
from aurora.extraction.models import DetectionMethod, DocumentDescriptor, DocumentType


class HTMLDetector(IDocumentDetector):
    """Detects HTML tags within the first 500 bytes chunk."""

    def process(self, input_data: bytes, context: PipelineContext) -> Optional[DocumentDescriptor]:
        first_chunk = input_data[:500].lower()
        if b"<html" in first_chunk or b"<!doctype html" in first_chunk:
            return DocumentDescriptor(
                doc_type=DocumentType.HTML,
                confidence=0.9,
                method=DetectionMethod.HEURISTIC,
                signature="<html",
            )
        return None
