"""Unit tests for the Document Normalization Subsystem."""

from datetime import datetime, timezone

import pytest

from aurora.extraction.models import ExtractedDocument
from aurora.models import ArtifactMetadata, FrameworkInfo, NormalizedDocument, PipelineProvenance
from aurora.models.enums import DocumentState
from aurora.models.metadata import FileMetadata
from aurora.normalization.models import NormalizationContext
from aurora.normalization.pipeline import (
    ControlCharacterNormalizer,
    LineEndingNormalizer,
    NormalizationPipeline,
    UnicodeNormalizer,
    WhitespaceNormalizer,
)


@pytest.fixture
def sample_extracted_doc() -> ExtractedDocument:
    """Fixture returning a sample ExtractedDocument."""
    import uuid
    meta = FileMetadata(source_path="test.txt", file_type="txt", char_count=20)
    framework = FrameworkInfo(module_name="TXTExtractor", module_version="0.1")
    provenance = PipelineProvenance(
        stage=DocumentState.EXTRACTED,
        producer="TXTExtractor",
        timestamp=datetime.now(timezone.utc),
        framework=framework,
    )
    artifact = ArtifactMetadata(
        artifact_id=uuid.uuid4(),
        checksum="dummy_checksum",
        created_at=provenance.timestamp,
    )
    return ExtractedDocument(
        doc_id="doc123",
        text="Sample Extracted Content\r\nLine 2",
        tables=[{"id": "tab1", "rows": 2}],
        images=[{"id": "img1", "caption": "chart"}],
        links=["http://example.com"],
        metadata=meta,
        provenance=provenance,
        artifact=artifact,
    )


def test_line_ending_normalization() -> None:
    """Standardizes CR/CRLF line endings to LF."""
    normalizer = LineEndingNormalizer()
    context = NormalizationContext()

    text = "line1\r\nline2\rline3\n"
    normalized = normalizer.process(text, context)
    assert normalized == "line1\nline2\nline3\n"


def test_control_character_normalization() -> None:
    """Removes control chars but keeps tabs and newlines."""
    normalizer = ControlCharacterNormalizer()
    context = NormalizationContext()

    text = "line1\x00\x1f\nline2\twith\x07bell"
    normalized = normalizer.process(text, context)
    assert normalized == "line1\nline2\twithbell"


def test_unicode_normalization() -> None:
    """Unifies Unicode representations (NFC standard)."""
    normalizer = UnicodeNormalizer()
    context = NormalizationContext()

    # "café" represented as combining characters (e + acute accent)
    decomposed = "cafe\u0301"
    normalized = normalizer.process(decomposed, context)
    # NFC cafe has single character é (\u00e9)
    assert normalized == "caf\u00e9"


def test_whitespace_normalization_collapses_spaces() -> None:
    """Collapses consecutive inline spaces."""
    normalizer = WhitespaceNormalizer()
    context = NormalizationContext()

    text = "Some    spaced   out   text."
    normalized = normalizer.process(text, context)
    assert normalized == "Some spaced out text."


def test_whitespace_normalization_preserves_code_blocks() -> None:
    """Preserves indentations and spaces inside Markdown code blocks."""
    normalizer = WhitespaceNormalizer()
    context = NormalizationContext()

    text = (
        "regular   text\n"
        "```python\n"
        "def   foo():\n"
        "    return   1\n"
        "```\n"
        "footer   text"
    )
    normalized = normalizer.process(text, context)
    expected = (
        "regular text\n"
        "```python\n"
        "def   foo():\n"
        "    return   1\n"
        "```\n"
        "footer text"
    )
    assert normalized == expected


def test_pipeline_execution_and_idempotency(sample_extracted_doc: ExtractedDocument) -> None:
    """Check sequential steps, idempotency, and provenance state transitions."""
    pipeline = NormalizationPipeline()
    context = NormalizationContext()

    # 1. Execute normalization
    normalized_doc = pipeline.normalize(sample_extracted_doc, context)

    assert isinstance(normalized_doc, NormalizedDocument)
    assert normalized_doc.text == "Sample Extracted Content\nLine 2"
    assert normalized_doc.provenance.stage == DocumentState.NORMALIZED
    assert normalized_doc.provenance.producer == "NormalizationPipeline"

    # 2. Check structural preservation
    assert normalized_doc.tables == sample_extracted_doc.tables
    assert normalized_doc.images == sample_extracted_doc.images
    assert normalized_doc.links == sample_extracted_doc.links

    # 3. Check stats metrics collection
    assert context.metrics["original_length"] == len(sample_extracted_doc.text)
    assert context.metrics["normalized_length"] == len(normalized_doc.text)

    # 4. Check idempotency: calling normalize again yields identical output
    extracted_again = sample_extracted_doc.model_copy(update={"text": normalized_doc.text})
    normalized_twice = pipeline.normalize(extracted_again, context)
    assert normalized_twice.text == normalized_doc.text
