"""DOCX document extractor plugin."""

from datetime import datetime, timezone
import hashlib
import io
import uuid
import docx2txt

from aurora.core.artifact import ArtifactMetadata
from aurora.core.exceptions import CorruptedDocumentError, ExtractionFailedError
from aurora.extraction.interfaces import IDocumentExtractor
from aurora.extraction.models import (
    DocumentType,
    ExtractedDocument,
    ExtractorCapability,
    ExtractorMetadata,
)
from aurora.models import FrameworkInfo, PipelineProvenance, RawDocument
from aurora.models.enums import DocumentState
from aurora.models.metadata import FileMetadata


class DOCXExtractor(IDocumentExtractor):
    """Production DOCX extractor parsing paragraph text, tables, and headers via docx2txt."""

    def extract(self, doc: RawDocument) -> ExtractedDocument:
        content_bytes = doc.content_bytes
        if not content_bytes:
            return self._build_empty_result(doc)

        try:
            byte_stream = io.BytesIO(content_bytes)
            extracted_raw = docx2txt.process(byte_stream)
        except Exception as e:
            raise CorruptedDocumentError(
                f"Failed to parse corrupt DOCX document '{doc.doc_id}': {e}"
            ) from e

        full_text = (extracted_raw or "").strip()

        # Update metadata
        custom_metadata = dict(doc.metadata.custom_metadata)
        custom_metadata.update({
            "sha256_checksum": doc.content_hash,
            "has_content": bool(full_text),
        })

        meta = FileMetadata(
            source_path=doc.metadata.source_path,
            file_type="docx",
            char_count=len(full_text),
            custom_metadata=custom_metadata,
            author=doc.metadata.author,
            created_at=doc.metadata.created_at,
        )

        provenance = PipelineProvenance(
            stage=DocumentState.EXTRACTED,
            producer="DOCXExtractor",
            timestamp=datetime.now(timezone.utc),
            framework=FrameworkInfo(
                module_name="DOCXExtractor",
                module_version="0.1.0",
            ),
            run_id=doc.provenance.run_id,
            execution_id=doc.provenance.execution_id,
        )

        content_hash = hashlib.sha256(full_text.encode("utf-8")).hexdigest()
        parent_ids = [doc.artifact.artifact_id] if doc.artifact else []
        artifact = ArtifactMetadata(
            artifact_id=uuid.uuid4(),
            parent_artifact_ids=parent_ids,
            derived_from=parent_ids,
            checksum=content_hash,
            created_at=provenance.timestamp,
            schema_version="1.0.0",
        )

        return ExtractedDocument(
            doc_id=doc.doc_id,
            text=full_text,
            tables=[],
            images=[],
            links=[],
            metadata=meta,
            provenance=provenance,
            artifact=artifact,
        )

    def _build_empty_result(self, doc: RawDocument) -> ExtractedDocument:
        meta = FileMetadata(
            source_path=doc.metadata.source_path,
            file_type="docx",
            char_count=0,
            custom_metadata=dict(doc.metadata.custom_metadata),
        )
        provenance = PipelineProvenance(
            stage=DocumentState.EXTRACTED,
            producer="DOCXExtractor",
            timestamp=datetime.now(timezone.utc),
            framework=FrameworkInfo(module_name="DOCXExtractor", module_version="0.1.0"),
        )
        parent_ids = [doc.artifact.artifact_id] if doc.artifact else []
        artifact = ArtifactMetadata(
            artifact_id=uuid.uuid4(),
            parent_artifact_ids=parent_ids,
            derived_from=parent_ids,
            checksum=doc.content_hash,
            created_at=provenance.timestamp,
        )
        return ExtractedDocument(
            doc_id=doc.doc_id,
            text="",
            tables=[],
            images=[],
            links=[],
            metadata=meta,
            provenance=provenance,
            artifact=artifact,
        )

    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            supported_type=DocumentType.DOCX,
            version="0.1.0",
            capabilities={ExtractorCapability.TEXT, ExtractorCapability.TABLES},
        )

