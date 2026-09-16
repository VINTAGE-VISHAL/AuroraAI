"""Plain Text document extractor plugin."""

from datetime import datetime, timezone

from aurora.core.exceptions import DecoderError
from aurora.extraction.interfaces import IDocumentExtractor
from aurora.extraction.models import ExtractedDocument, ExtractorCapability, ExtractorMetadata
from aurora.models import FrameworkInfo, PipelineProvenance, RawDocument
from aurora.models.enums import DocumentState


class TXTExtractor(IDocumentExtractor):
    """Parses raw text documents by decoding binary payload using UTF-8."""

    def extract(self, doc: RawDocument) -> ExtractedDocument:
        try:
            text = doc.content_bytes.decode("utf-8")
        except UnicodeDecodeError as e:
            raise DecoderError(f"Failed to decode TXT bytes using UTF-8: {e}") from e

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

        import hashlib
        import uuid

        from aurora.models import ArtifactMetadata

        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        artifact = ArtifactMetadata(
            artifact_id=uuid.uuid4(),
            parent_artifact_ids=[doc.artifact.artifact_id],
            derived_from=[doc.artifact.artifact_id],
            checksum=content_hash,
            created_at=provenance.timestamp,
            schema_version="1.0.0",
        )

        return ExtractedDocument(
            doc_id=doc.doc_id,
            text=text,
            tables=[],
            images=[],
            links=[],
            metadata=doc.metadata,
            provenance=provenance,
            artifact=artifact,
        )

    def get_metadata(self) -> ExtractorMetadata:
        from aurora.extraction.models import DocumentType
        return ExtractorMetadata(
            supported_type=DocumentType.TXT,
            version="0.1.0",
            capabilities={ExtractorCapability.TEXT},
        )

