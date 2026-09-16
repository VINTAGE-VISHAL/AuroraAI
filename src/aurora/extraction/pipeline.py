"""Orchestrator pipeline executing format signature detectors in priority order."""

from typing import List, Optional

from aurora.core.pipeline import BasePipeline, PipelineContext, PipelineResult
from aurora.extraction.detectors.html import HTMLDetector
from aurora.extraction.detectors.pdf import PDFDetector
from aurora.extraction.detectors.text import TextDetector
from aurora.extraction.detectors.zip import ZipDetector
from aurora.extraction.interfaces import IDocumentDetector
from aurora.extraction.models import DetectionMethod, DocumentDescriptor, DocumentType


class DetectionPipeline(BasePipeline[bytes, DocumentDescriptor]):
    """Orchestrates ordered execution of format signature detectors."""

    def __init__(self, detectors: Optional[List[IDocumentDetector]] = None) -> None:
        if detectors is None:
            # Default priority sequence: PDF -> ZIP -> HTML -> TEXT
            default_detectors: List[IDocumentDetector] = [
                PDFDetector(),
                ZipDetector(),
                HTMLDetector(),
                TextDetector(),
            ]
            super().__init__(default_detectors)  # type: ignore
        else:
            super().__init__(detectors)  # type: ignore

    def execute(
        self, input_data: bytes, context: PipelineContext
    ) -> PipelineResult[DocumentDescriptor]:
        """Run through detector chain in sequence. Fallback to UNKNOWN if unmatched."""
        for detector in self.steps:
            descriptor = detector.process(input_data, context)
            if descriptor is not None:
                return PipelineResult(
                    result=descriptor,
                    metrics=context.metrics,
                    warnings=context.warnings,
                    diagnostics=context.diagnostics,
                )

        fallback = DocumentDescriptor(
            doc_type=DocumentType.UNKNOWN,
            confidence=0.0,
            method=DetectionMethod.FALLBACK,
            signature=None,
        )
        return PipelineResult(
            result=fallback,
            metrics=context.metrics,
            warnings=context.warnings,
            diagnostics=context.diagnostics,
        )
