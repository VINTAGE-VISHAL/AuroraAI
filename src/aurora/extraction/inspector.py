"""Format inspector coordinating detection via the DetectionPipeline."""

from typing import Optional

from aurora.extraction.models import DetectionMethod, DocumentDescriptor, DocumentType
from aurora.extraction.pipeline import DetectionPipeline
from aurora.models.document import RawDocument


class DocumentInspector:
    """Coordinates RawDocument classification by invoking the DetectionPipeline."""

    def __init__(self, pipeline: Optional[DetectionPipeline] = None) -> None:
        self.pipeline = pipeline or DetectionPipeline()

    def inspect(self, doc: RawDocument) -> DocumentDescriptor:
        """Inspect doc using the detection pipeline."""
        data = doc.content_bytes
        if not data:
            return DocumentDescriptor(
                doc_type=DocumentType.UNKNOWN,
                confidence=0.0,
                method=DetectionMethod.FALLBACK,
                signature=None,
            )
        from aurora.core.pipeline import PipelineContext
        context = PipelineContext()
        return self.pipeline.execute(data, context).result
