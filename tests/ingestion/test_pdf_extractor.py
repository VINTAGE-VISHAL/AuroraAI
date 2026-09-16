"""Unit tests for the PDFExtractor Phase A component."""

import os
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from aurora.core.artifact import ArtifactMetadata
from aurora.core.exceptions import InterfaceError
from aurora.ingestion.pdf_extractor import PDFExtractor
from aurora.models import DocumentState, FileMetadata, PipelineProvenance, RawDocument
from aurora.models.provenance import FrameworkInfo


def test_pdf_extractor_success(tmp_path) -> None:
    """Verify that PDFExtractor successfully extracts pages from a standard PDF."""
    pdf_file = tmp_path / "chapter1.pdf"
    pdf_file.write_bytes(b"dummy_pdf_content")

    # Construct RawDocument input
    meta = FileMetadata(
        source_path=str(pdf_file),
        file_type="pdf",
        char_count=0,
    )
    provenance = PipelineProvenance(
        stage=DocumentState.LOADED,
        producer="DocumentLoader",
        timestamp=datetime.now(timezone.utc),
        framework=FrameworkInfo(module_name="loader", module_version="0.1.0"),
    )
    artifact = ArtifactMetadata(
        artifact_id=uuid.uuid4(),
        checksum="dummy_checksum",
        created_at=datetime.now(timezone.utc),
    )
    raw_doc = RawDocument(
        doc_id="dummy_hash",
        source_id="source_123",
        uri=f"file:///{str(pdf_file).replace(os.sep, '/')}",
        content_bytes=b"dummy_pdf_content",
        content_hash="dummy_hash",
        metadata=meta,
        provenance=provenance,
        artifact=artifact,
    )

    mock_doc = MagicMock()
    mock_doc.__len__.return_value = 2

    # Mock the context manager behavior of fitz.open
    mock_doc.__enter__.return_value = mock_doc
    mock_doc.__exit__.return_value = None
    mock_doc.is_encrypted = False

    mock_page1 = MagicMock()
    mock_page1.get_text.return_value = "Page 1 Content\nHello"
    mock_page2 = MagicMock()
    mock_page2.get_text.return_value = "Page 2 Content\nWorld"

    mock_doc.load_page.side_effect = [mock_page1, mock_page2]

    extractor = PDFExtractor()

    with patch("fitz.open", return_value=mock_doc) as mock_open:
        extracted = extractor.extract(raw_doc)
        
        # In context manager, fitz.open is called with stream and filetype parameters
        mock_open.assert_called_once_with(stream=b"dummy_pdf_content", filetype="pdf")
        assert len(extracted.pages) == 2
        assert extracted.pages[0] == "Page 1 Content\nHello"
        assert extracted.pages[1] == "Page 2 Content\nWorld"
        assert extracted.metadata.file_type == "pdf"
        assert extracted.metadata.char_count == len("Page 1 Content\nHello") + len("Page 2 Content\nWorld")
        assert extracted.provenance.stage == DocumentState.EXTRACTED


def test_pdf_extractor_encrypted(tmp_path) -> None:
    """Verify that PDFExtractor raises InterfaceError when encountering encrypted PDFs."""
    pdf_file = tmp_path / "encrypted.pdf"
    
    meta = FileMetadata(source_path=str(pdf_file), file_type="pdf", char_count=0)
    provenance = PipelineProvenance(
        stage=DocumentState.LOADED,
        producer="DocumentLoader",
        timestamp=datetime.now(timezone.utc),
        framework=FrameworkInfo(module_name="loader", module_version="0.1.0"),
    )
    artifact = ArtifactMetadata(
        artifact_id=uuid.uuid4(),
        checksum="dummy_checksum",
        created_at=datetime.now(timezone.utc),
    )
    raw_doc = RawDocument(
        doc_id="dummy_hash",
        source_id="source_123",
        uri=f"file:///{str(pdf_file).replace(os.sep, '/')}",
        content_bytes=b"dummy_pdf_content",
        content_hash="dummy_hash",
        metadata=meta,
        provenance=provenance,
        artifact=artifact,
    )

    mock_doc = MagicMock()
    mock_doc.__enter__.return_value = mock_doc
    mock_doc.__exit__.return_value = None
    mock_doc.is_encrypted = True

    extractor = PDFExtractor()

    with patch("fitz.open", return_value=mock_doc):
        with pytest.raises(InterfaceError, match="is encrypted"):
            extractor.extract(raw_doc)


def test_pdf_extractor_empty_bytes() -> None:
    """Verify that PDFExtractor raises InterfaceError when RawDocument contains empty bytes."""
    meta = FileMetadata(source_path="mock.pdf", file_type="pdf", char_count=0)
    provenance = PipelineProvenance(
        stage=DocumentState.LOADED,
        producer="DocumentLoader",
        timestamp=datetime.now(timezone.utc),
        framework=FrameworkInfo(module_name="loader", module_version="0.1.0"),
    )
    artifact = ArtifactMetadata(
        artifact_id=uuid.uuid4(),
        checksum="dummy_checksum",
        created_at=datetime.now(timezone.utc),
    )
    raw_doc = RawDocument(
        doc_id="dummy_hash",
        source_id="source_123",
        uri="file:///mock.pdf",
        content_bytes=b"",
        content_hash="dummy_hash",
        metadata=meta,
        provenance=provenance,
        artifact=artifact,
    )

    extractor = PDFExtractor()
    with pytest.raises(InterfaceError, match="Content bytes are empty"):
        extractor.extract(raw_doc)
