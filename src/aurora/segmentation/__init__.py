"""Structural document segmentation subsystem parsing documents into elements."""

from datetime import datetime, timezone
import hashlib
from typing import List
import uuid

from aurora.config.settings import Settings
from aurora.core.artifact import ArtifactMetadata
from aurora.core.pipeline import PipelineContext
from aurora.interfaces.base import IPipelineComponent
from aurora.models.document import NormalizedDocument, ProcessedDocument, StructuredDocument
from aurora.models.enums import DocumentState
from aurora.models.provenance import FrameworkInfo, PipelineProvenance
from aurora.registry.module_registry import ModuleRegistry
from aurora.segmentation.interfaces import ISegmentationStep
from aurora.segmentation.pipeline import (
    CodeBlockSegmentationStep,
    HeaderSegmentationStep,
    ParagraphSegmentationStep,
    SegmentationPipeline,
)


@ModuleRegistry.register("segmentation")
class DefaultSegmenter(IPipelineComponent[List[ProcessedDocument], List[StructuredDocument]]):
    """Default pipeline component executing document segmentation."""

    def __init__(self, config: Settings) -> None:
        self.config = config
        self.pipeline = SegmentationPipeline()

    def run(self, input_data: List[ProcessedDocument]) -> List[StructuredDocument]:
        """Convert ProcessedDocuments to StructuredDocuments via SegmentationPipeline."""
        structured_docs = []
        for doc in input_data:
            prov = PipelineProvenance(
                stage=DocumentState.NORMALIZED,
                producer="Preprocessor",
                timestamp=datetime.now(timezone.utc),
                framework=FrameworkInfo(module_name="Preprocessor", module_version="0.1.0"),
            )
            content_hash = hashlib.sha256(doc.content.encode("utf-8")).hexdigest()
            artifact = ArtifactMetadata(
                artifact_id=uuid.uuid4(),
                checksum=content_hash,
                created_at=prov.timestamp,
                schema_version="1.0.0",
            )
            norm_doc = NormalizedDocument(
                doc_id=doc.doc_id,
                text=doc.content,
                metadata=doc.metadata,
                provenance=prov,
                artifact=artifact,
            )
            
            context = PipelineContext()
            result = self.pipeline.execute(norm_doc, context)
            structured_docs.append(result.result)

        return structured_docs


__all__ = [
    "ISegmentationStep",
    "SegmentationPipeline",
    "HeaderSegmentationStep",
    "CodeBlockSegmentationStep",
    "ParagraphSegmentationStep",
    "DefaultSegmenter",
]
