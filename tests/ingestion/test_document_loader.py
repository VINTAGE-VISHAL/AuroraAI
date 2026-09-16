"""Unit tests for DocumentLoader and core metrics."""

import time
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from aurora.core.exceptions import (
    DocumentLoadError,
    PermissionDeniedError,
    UnreadableDocumentError,
    UnsupportedDocumentError,
)
from aurora.core.metrics import MetricsCollector
from aurora.ingestion.document_loader import DocumentLoader
from aurora.models.enums import DocumentState
from aurora.models.source import SourceDocument, SourceMetadata


@pytest.fixture
def metrics() -> MetricsCollector:
    """Fixture returning a fresh metrics collector."""
    return MetricsCollector()


@pytest.fixture
def loader(metrics: MetricsCollector) -> DocumentLoader:
    """Fixture returning a DocumentLoader instance."""
    return DocumentLoader(metrics)


@pytest.fixture
def sample_source() -> SourceDocument:
    """Fixture returning a mock source document."""
    meta = SourceMetadata(
        uri="file:///mock/path/doc.pdf",
        size_bytes=100,
        file_format="pdf",
        checksum="filechecksum123",
        registered_at=time.time(),
        last_verified=time.time(),
    )
    return SourceDocument(
        doc_id="doc_id_123",
        uri="file:///mock/path/doc.pdf",
        checksum="filechecksum123",
        subject_name="math",
        metadata=meta,
    )


def test_zero_byte_file_load(
    tmp_path: Path, loader: DocumentLoader, metrics: MetricsCollector
) -> None:
    """Load a zero-byte file and check metadata."""
    test_file = tmp_path / "empty.txt"
    test_file.write_bytes(b"")

    source = SourceDocument(
        doc_id="doc1",
        uri=test_file.resolve().as_uri(),
        checksum="chksum",
        subject_name="test",
        metadata=SourceMetadata(
            uri=test_file.resolve().as_uri(),
            size_bytes=0,
            file_format="txt",
            checksum="chksum",
            registered_at=time.time(),
            last_verified=time.time(),
        )
    )

    raw_doc = loader.load(source)
    assert raw_doc.content_bytes == b""
    expected_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert raw_doc.content_hash == expected_hash
    assert raw_doc.state == DocumentState.LOADED

    snapshot = metrics.emit_snapshot()
    assert snapshot.files_loaded == 1
    assert snapshot.bytes_read == 0


def test_binary_file_load(tmp_path: Path, loader: DocumentLoader) -> None:
    """Load binary content and verify correct content hash."""
    test_file = tmp_path / "binary.bin"
    binary_data = b"\x00\x01\x02\x03\xff"
    test_file.write_bytes(binary_data)

    source = SourceDocument(
        doc_id="doc2",
        uri=test_file.resolve().as_uri(),
        checksum="chk",
        subject_name="test",
        metadata=SourceMetadata(
            uri=test_file.resolve().as_uri(),
            size_bytes=5,
            file_format="bin",
            checksum="chk",
            registered_at=time.time(),
            last_verified=time.time(),
        )
    )

    raw_doc = loader.load(source)
    assert raw_doc.content_bytes == binary_data
    # check hash
    import hashlib
    expected_hash = hashlib.sha256(binary_data).hexdigest()
    assert raw_doc.content_hash == expected_hash


def test_unsupported_uri_scheme(loader: DocumentLoader) -> None:
    """Loading non-file URIs raises UnsupportedDocumentError."""
    source = SourceDocument(
        doc_id="doc3",
        uri="s3://bucket/doc.pdf",
        checksum="chk",
        subject_name="test",
        metadata=SourceMetadata(
            uri="s3://bucket/doc.pdf",
            size_bytes=10,
            file_format="pdf",
            checksum="chk",
            registered_at=time.time(),
            last_verified=time.time(),
        )
    )
    with pytest.raises(UnsupportedDocumentError):
        loader.load(source)


def test_missing_file_load(loader: DocumentLoader) -> None:
    """Loading missing files raises DocumentLoadError."""
    source = SourceDocument(
        doc_id="doc4",
        uri="file:///non/existent/file.txt",
        checksum="chk",
        subject_name="test",
        metadata=SourceMetadata(
            uri="file:///non/existent/file.txt",
            size_bytes=10,
            file_format="txt",
            checksum="chk",
            registered_at=time.time(),
            last_verified=time.time(),
        )
    )
    with pytest.raises(DocumentLoadError):
        loader.load(source)


def test_permission_denied_load(tmp_path: Path, loader: DocumentLoader) -> None:
    """Permission issues raise PermissionDeniedError."""
    test_file = tmp_path / "locked.txt"
    test_file.write_text("locked")

    source = SourceDocument(
        doc_id="doc5",
        uri=test_file.resolve().as_uri(),
        checksum="chk",
        subject_name="test",
        metadata=SourceMetadata(
            uri=test_file.resolve().as_uri(),
            size_bytes=6,
            file_format="txt",
            checksum="chk",
            registered_at=time.time(),
            last_verified=time.time(),
        )
    )

    from unittest.mock import patch
    with patch("builtins.open", side_effect=PermissionError("Permission Denied")):
        with pytest.raises(PermissionDeniedError):
            loader.load(source)


def test_unreadable_file_error(tmp_path: Path, loader: DocumentLoader) -> None:
    """General reading failures raise UnreadableDocumentError."""
    test_file = tmp_path / "corrupt.txt"
    test_file.write_text("corrupt")

    source = SourceDocument(
        doc_id="doc6",
        uri=test_file.resolve().as_uri(),
        checksum="chk",
        subject_name="test",
        metadata=SourceMetadata(
            uri=test_file.resolve().as_uri(),
            size_bytes=7,
            file_format="txt",
            checksum="chk",
            registered_at=time.time(),
            last_verified=time.time(),
        )
    )

    from unittest.mock import patch
    with patch("builtins.open", side_effect=IOError("Corrupt sector")):
        with pytest.raises(UnreadableDocumentError):
            loader.load(source)


def test_provenance_and_immutability(tmp_path: Path, loader: DocumentLoader) -> None:
    """Verify that RawDocument models are read-only and provenance fields map correctly."""
    test_file = tmp_path / "frozen.txt"
    test_file.write_text("frozen payload")

    uuid4()
    uuid4()

    source = SourceDocument(
        doc_id="doc7",
        uri=test_file.resolve().as_uri(),
        checksum="chk",
        subject_name="test",
        metadata=SourceMetadata(
            uri=test_file.resolve().as_uri(),
            size_bytes=14,
            file_format="txt",
            checksum="chk",
            registered_at=time.time(),
            last_verified=time.time(),
        )
    )

    raw_doc = loader.load(source)
    assert raw_doc.provenance.stage == DocumentState.LOADED
    assert raw_doc.provenance.producer == "DocumentLoader"
    assert raw_doc.provenance.framework.framework_name == "AuroraEngine"
    assert raw_doc.provenance.framework.module_name == "DocumentLoader"

    # Enforce Immutability: Mutating frozen model properties raises ValidationError/TypeError
    with pytest.raises((ValidationError, TypeError)):
        # Pydantic v2 frozen model raises ValidationError/TypeError on mutation
        raw_doc.uri = "file:///mutated"  # type: ignore


def test_metrics_collection_timing_and_snapshot(
    tmp_path: Path, loader: DocumentLoader, metrics: MetricsCollector
) -> None:
    """Check timing contexts, snapshot aggregation, and resets."""
    test_file = tmp_path / "timer.txt"
    test_file.write_text("data payload")

    source = SourceDocument(
        doc_id="doc8",
        uri=test_file.resolve().as_uri(),
        checksum="chk",
        subject_name="test",
        metadata=SourceMetadata(
            uri=test_file.resolve().as_uri(),
            size_bytes=12,
            file_format="txt",
            checksum="chk",
            registered_at=time.time(),
            last_verified=time.time(),
        )
    )

    loader.load(source)

    # Check snapshotted values
    snapshot = metrics.emit_snapshot()
    assert snapshot.files_loaded == 1
    assert snapshot.bytes_read == 12
    assert snapshot.failures == 0
    assert snapshot.average_load_time > 0.0

    # Reset metrics and verify clean state
    metrics.reset()
    clean_snap = metrics.emit_snapshot()
    assert clean_snap.files_loaded == 0
    assert clean_snap.bytes_read == 0
    assert clean_snap.average_load_time == 0.0
