"""Plain Text document extractor plugin."""

from datetime import datetime, timezone
import hashlib
import uuid

from aurora.core.artifact import ArtifactMetadata
from aurora.core.exceptions import DecoderError
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


class TXTExtractor(IDocumentExtractor):
    """Parses raw text documents by decoding binary payload using UTF-8 / fallback encodings."""

    def extract(self, doc: RawDocument) -> ExtractedDocument:
        content_bytes = doc.content_bytes
        if not content_bytes:
            return self._build_empty_result(doc)

        text: str = ""
        try:
            text = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = content_bytes.decode("utf-8-sig")
            except UnicodeDecodeError:
                try:
                    text = content_bytes.decode("latin-1")
                except Exception as e:
                    raise DecoderError(f"Failed to decode TXT bytes: {e}") from e

        text = text.replace("\r\n", "\n").replace("\r", "\n")

        framework = FrameworkInfo(
            module_name="TXTExtractor",
            module_version="0.1.0",
        )
        provenance = PipelineProvenance(
            stage=DocumentState.EXTRACTED,
            producer="TXTExtractor",
            timestamp=datetime.now(timezone.utc),
            framework=framework,
            run_id=doc.provenance.run_id,
            execution_id=doc.provenance.execution_id,
        )

        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        parent_ids = [doc.artifact.artifact_id] if doc.artifact else []
        artifact = ArtifactMetadata(
            artifact_id=uuid.uuid4(),
            parent_artifact_ids=parent_ids,
            derived_from=parent_ids,
            checksum=content_hash,
            created_at=provenance.timestamp,
            schema_version="1.0.0",
        )

        meta = FileMetadata(
            source_path=doc.metadata.source_path,
            file_type="txt",
            char_count=len(text),
            custom_metadata=dict(doc.metadata.custom_metadata),
            author=doc.metadata.author,
            created_at=doc.metadata.created_at,
        )

        return ExtractedDocument(
            doc_id=doc.doc_id,
            text=text,
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
            file_type="txt",
            char_count=0,
            custom_metadata=dict(doc.metadata.custom_metadata),
        )
        provenance = PipelineProvenance(
            stage=DocumentState.EXTRACTED,
            producer="TXTExtractor",
            timestamp=datetime.now(timezone.utc),
            framework=FrameworkInfo(module_name="TXTExtractor", module_version="0.1.0"),
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
            supported_type=DocumentType.TXT,
            version="0.1.0",
            capabilities={ExtractorCapability.TEXT},
        )


