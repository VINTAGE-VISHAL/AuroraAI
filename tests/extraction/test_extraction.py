"""Unit tests for the Document Ingestion / Extraction Subsystem."""

import io
import zipfile
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from aurora.core.exceptions import RegistryError, UnsupportedExtractionError
from aurora.extraction.inspector import DocumentInspector
from aurora.extraction.models import DetectionMethod, DocumentType, ExtractedDocument
from aurora.extraction.plugins.txt import TXTExtractor
from aurora.extraction.registry import ExtractorRegistry
from aurora.models import ArtifactMetadata, FrameworkInfo, PipelineProvenance, RawDocument
from aurora.models.enums import DocumentState
from aurora.models.metadata import FileMetadata


@pytest.fixture
def sample_raw_doc() -> RawDocument:
    """Fixture returning a base RawDocument instance."""
    import uuid
    valid_meta = FileMetadata(source_path="src/file.txt", file_type="txt", char_count=12)
    framework = FrameworkInfo(module_name="test", module_version="0.1")
    provenance = PipelineProvenance(
        stage=DocumentState.LOADED,
        producer="test",
        timestamp=datetime.now(timezone.utc),
        framework=framework,
    )
    artifact = ArtifactMetadata(
        artifact_id=uuid.uuid4(),
        checksum="hash123",
        created_at=provenance.timestamp,
    )
    return RawDocument(
        doc_id="doc1",
        source_id="src1",
        uri="file:///src/file.txt",
        content_bytes=b"Hello World!",
        content_hash="hash123",
        state=DocumentState.LOADED,
        metadata=valid_meta,
        provenance=provenance,
        artifact=artifact,
    )


def test_inspector_pdf_classification(sample_raw_doc: RawDocument) -> None:
    """Validate PDF header detection."""
    inspector = DocumentInspector()
    pdf_bytes = b"%PDF-1.4\ncontent"
    # Create doc with PDF bytes
    doc = sample_raw_doc.model_copy(update={"content_bytes": pdf_bytes})

    descriptor = inspector.inspect(doc)
    assert descriptor.doc_type == DocumentType.PDF
    assert descriptor.confidence == 1.0
    assert descriptor.method == DetectionMethod.MAGIC_BYTES
    assert descriptor.signature == "%PDF-"


def test_inspector_docx_classification(sample_raw_doc: RawDocument) -> None:
    """Validate DOCX sub-inspection classifications."""
    inspector = DocumentInspector()

    # Create in-memory zip file representing docx
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("word/document.xml", "<w:document></w:document>")
        zf.writestr("[Content_Types].xml", "types")

    doc = sample_raw_doc.model_copy(update={"content_bytes": zip_buffer.getvalue()})
    descriptor = inspector.inspect(doc)
    assert descriptor.doc_type == DocumentType.DOCX
    assert descriptor.confidence == 1.0
    assert descriptor.method == DetectionMethod.HEURISTIC


def test_inspector_xlsx_classification(sample_raw_doc: RawDocument) -> None:
    """Validate XLSX Excel zip classification."""
    inspector = DocumentInspector()

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("xl/workbook.xml", "workbook")

    doc = sample_raw_doc.model_copy(update={"content_bytes": zip_buffer.getvalue()})
    descriptor = inspector.inspect(doc)
    assert descriptor.doc_type == DocumentType.XLSX


def test_inspector_generic_zip_classification(sample_raw_doc: RawDocument) -> None:
    """Validate zip file with no docx structures classified as standard ZIP."""
    inspector = DocumentInspector()

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("random.txt", "data")

    doc = sample_raw_doc.model_copy(update={"content_bytes": zip_buffer.getvalue()})
    descriptor = inspector.inspect(doc)
    assert descriptor.doc_type == DocumentType.ZIP


def test_inspector_bad_zip_data(sample_raw_doc: RawDocument) -> None:
    """Bad ZIP header defaults to UNKNOWN fallback classification."""
    inspector = DocumentInspector()
    corrupt_zip = b"PK\x03\x04notazip"

    doc = sample_raw_doc.model_copy(update={"content_bytes": corrupt_zip})
    descriptor = inspector.inspect(doc)
    assert descriptor.doc_type == DocumentType.UNKNOWN
    assert descriptor.confidence == 0.1
    assert descriptor.method == DetectionMethod.FALLBACK


def test_inspector_html_classification(sample_raw_doc: RawDocument) -> None:
    """HTML tag discovery check."""
    inspector = DocumentInspector()
    html_bytes = b"<!DOCTYPE html><html><body>hello</body></html>"

    doc = sample_raw_doc.model_copy(update={"content_bytes": html_bytes})
    descriptor = inspector.inspect(doc)
    assert descriptor.doc_type == DocumentType.HTML
    assert descriptor.confidence == 0.9


def test_inspector_markdown_classification(sample_raw_doc: RawDocument) -> None:
    """Markdown header discovery check."""
    inspector = DocumentInspector()
    md_bytes = b"# Heading\nSome **bold** text."

    doc = sample_raw_doc.model_copy(update={"content_bytes": md_bytes})
    descriptor = inspector.inspect(doc)
    assert descriptor.doc_type == DocumentType.MARKDOWN
    assert descriptor.confidence == 0.8


def test_inspector_safe_fallback_on_random_bytes(sample_raw_doc: RawDocument) -> None:
    """Non-decodable random bytes fallback to UNKNOWN with zero confidence."""
    inspector = DocumentInspector()
    random_bytes = b"\x80\xff\x90\x00\x12"

    doc = sample_raw_doc.model_copy(update={"content_bytes": random_bytes})
    descriptor = inspector.inspect(doc)
    assert descriptor.doc_type == DocumentType.UNKNOWN
    assert descriptor.confidence == 0.0
    assert descriptor.method == DetectionMethod.FALLBACK


def test_registry_registration_and_lookup() -> None:
    """Test registry binds classes correctly and blocks duplicates."""
    ExtractorRegistry.clear()

    ExtractorRegistry.register(DocumentType.TXT, TXTExtractor)

    # Assert correct lookup
    extractor_cls = ExtractorRegistry.get_extractor_class(DocumentType.TXT)
    assert extractor_cls == TXTExtractor

    # Duplicate registration policy throws RegistryError
    with pytest.raises(RegistryError):
        ExtractorRegistry.register(DocumentType.TXT, TXTExtractor)

    # Missing lookup raises UnsupportedExtractionError
    with pytest.raises(UnsupportedExtractionError):
        ExtractorRegistry.get_extractor_class(DocumentType.PDF)


def test_txt_extractor_transitions_to_extracted(sample_raw_doc: RawDocument) -> None:
    """TXT Extractor resolves content and transitions state to EXTRACTED."""
    extractor = TXTExtractor()
    extracted_doc = extractor.extract(sample_raw_doc)

    assert isinstance(extracted_doc, ExtractedDocument)
    assert extracted_doc.text == "Hello World!"
    assert extracted_doc.provenance.stage == DocumentState.EXTRACTED
    assert extracted_doc.provenance.producer == "TXTExtractor"


def test_extraction_immutability(sample_raw_doc: RawDocument) -> None:
    """ExtractedDocument enforces frozen read-only configuration."""
    extractor = TXTExtractor()
    extracted_doc = extractor.extract(sample_raw_doc)

    with pytest.raises((ValidationError, TypeError)):
        extracted_doc.text = "Attempted Mutation"  # type: ignore
