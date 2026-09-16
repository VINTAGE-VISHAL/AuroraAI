"""Extraction subsystem components mapping RawDocuments to parsed structures."""

from aurora.extraction.inspector import DocumentInspector
from aurora.extraction.interfaces import IDocumentDetector, IDocumentExtractor
from aurora.extraction.models import (
    DetectionMethod,
    DocumentDescriptor,
    DocumentType,
    ExtractedDocument,
    ExtractorCapability,
    ExtractorMetadata,
)
from aurora.extraction.pipeline import DetectionPipeline
from aurora.extraction.registry import ExtractorRegistry

__all__ = [
    "DocumentType",
    "DetectionMethod",
    "DocumentDescriptor",
    "ExtractorCapability",
    "ExtractorMetadata",
    "ExtractedDocument",
    "IDocumentExtractor",
    "IDocumentDetector",
    "ExtractorRegistry",
    "DocumentInspector",
    "DetectionPipeline",
]
