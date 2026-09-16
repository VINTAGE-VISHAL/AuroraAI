"""Document Loader implementation executing raw file streams reads."""

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

from aurora.core.exceptions import (
    DocumentLoadError,
    PermissionDeniedError,
    UnreadableDocumentError,
    UnsupportedDocumentError,
)
from aurora.core.metrics import MetricsCollector
from aurora.interfaces.loader import IDocumentLoader
from aurora.models import FrameworkInfo, PipelineProvenance, RawDocument
from aurora.models.enums import DocumentState
from aurora.models.metadata import FileMetadata
from aurora.models.source import SourceDocument


class DocumentLoader(IDocumentLoader):
    """Loads source documents from URIs into memory as immutable RawDocuments."""

    def __init__(self, metrics_collector: MetricsCollector) -> None:
        self.metrics = metrics_collector

    def load(self, source: SourceDocument) -> RawDocument:
        """Read URI stream, record loaded stats/timings, and return RawDocument."""
        parsed = urlparse(source.uri)
        if parsed.scheme != "file":
            self.metrics.increment("failures")
            raise UnsupportedDocumentError(f"Unsupported URI scheme: {parsed.scheme}")

        filepath = Path(url2pathname(parsed.path))

        with self.metrics.time_block("document_load_time"):
            try:
                with open(filepath, "rb") as f:
                    content_bytes = f.read()
            except PermissionError as e:
                self.metrics.increment("failures")
                raise PermissionDeniedError(f"Permission denied accessing path: {filepath}") from e
            except FileNotFoundError as e:
                self.metrics.increment("failures")
                raise DocumentLoadError(f"Source file not found: {filepath}") from e
            except Exception as e:
                self.metrics.increment("failures")
                raise UnreadableDocumentError(f"Corrupted or unreadable stream: {filepath}") from e

        content_hash = hashlib.sha256(content_bytes).hexdigest()

        # Record success metrics
        self.metrics.increment("files_loaded")
        self.metrics.increment("bytes_read", len(content_bytes))

        # Setup provenance
        framework = FrameworkInfo(
            module_name="DocumentLoader",
            module_version="0.1.0",
        )
        provenance = PipelineProvenance(
            stage=DocumentState.LOADED,
            producer="DocumentLoader",
            timestamp=datetime.now(timezone.utc),
            framework=framework,
        )

        file_meta = FileMetadata(
            source_path=source.uri,
            file_type=source.metadata.file_format,
            char_count=len(content_bytes),
        )

        import uuid

        from aurora.models import ArtifactMetadata

        artifact = ArtifactMetadata(
            artifact_id=uuid.uuid4(),
            checksum=content_hash,
            created_at=provenance.timestamp,
            schema_version="1.0.0",
        )

        return RawDocument(
            doc_id=source.doc_id,
            source_id=source.doc_id,
            uri=source.uri,
            content_bytes=content_bytes,
            content_hash=content_hash,
            state=DocumentState.LOADED,
            metadata=file_meta,
            provenance=provenance,
            artifact=artifact,
        )
