"""Plain Text and Markdown format signature detector."""

from typing import Optional

from aurora.core.pipeline import PipelineContext
from aurora.extraction.interfaces import IDocumentDetector
from aurora.extraction.models import DetectionMethod, DocumentDescriptor, DocumentType


class TextDetector(IDocumentDetector):
    """Detects Markdown elements or falls back to plain UTF-8 text."""

    def process(self, input_data: bytes, context: PipelineContext) -> Optional[DocumentDescriptor]:
        try:
            decoded = input_data.decode("utf-8")
            if decoded.startswith("# ") or "\n# " in decoded or "**" in decoded:
                return DocumentDescriptor(
                    doc_type=DocumentType.MARKDOWN,
                    confidence=0.8,
                    method=DetectionMethod.HEURISTIC,
                    signature="markdown-headers",
                )
            return DocumentDescriptor(
                doc_type=DocumentType.TXT,
                confidence=0.7,
                method=DetectionMethod.HEURISTIC,
                signature="utf8-text",
            )
        except UnicodeDecodeError:
            return None
