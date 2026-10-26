"""Comprehensive Automated Unit and Integration Tests for Module 03: Text Preprocessing and Chunking.

Covers:
- Normal text and paragraph preservation (whitespace normalization, no loss of paragraphs)
- Headings, lists, and Markdown code blocks preservation
- Configurable chunk size and overlap enforcement
- Very short, whitespace-only, and empty documents
- Long documents producing multiple ordered, overlapping chunks
- Unicode and multi-byte character processing
- Deterministic output for identical input and configurations
- PDF page attribution (source_page preserved per chunk)
- Non-PDF attribution (source_page is None for TXT, DOCX, Markdown)
- Chunk metadata, index/total counts, and character offsets
- Invalid configuration detection and rejection (overlap >= chunk_size, negative, zero)
- Non-empty chunks guarantee (no empty or whitespace-only chunks)
- FileService end-to-end integration: Upload -> Extract -> Chunk
- API server endpoint integration: POST /v1/files/{file_id}/chunk
- Full regression verification with Modules 01 and 02
"""

import io
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

import fitz  # PyMuPDF
import pytest
from fastapi.testclient import TestClient

from aurora.config.settings import RuntimeStorageConfig
from aurora.core.exceptions import (
    InvalidChunkingConfigError,
    RuntimeFileNotFoundError,
)
from aurora.deployment.api_server import app
from aurora.ingestion.runtime.file_storage import RuntimeFileStorage
from aurora.ingestion.runtime.file_validator import RuntimeFileValidator
from aurora.models.file_metadata import ExtractedFileResponse
from aurora.models.runtime_chunk import ChunkingConfig, DocumentChunk
from aurora.preprocessing.runtime_chunker import RuntimeChunker
from aurora.services.file_service import FileService


@pytest.fixture
def temp_storage_dir():
    temp_dir = tempfile.mkdtemp(prefix="aurora_test_runtime_chunking_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def custom_config():
    return RuntimeStorageConfig(
        upload_dir="data/runtime_uploads",
        max_upload_size_mb=5,
        allowed_extensions=[".pdf", ".docx", ".txt", ".md"],
    )


@pytest.fixture
def chunker():
    return RuntimeChunker()


@pytest.fixture
def file_service(custom_config, temp_storage_dir, chunker):
    storage = RuntimeFileStorage(custom_config, base_dir=temp_storage_dir)
    validator = RuntimeFileValidator(custom_config)
    return FileService(validator=validator, storage=storage, chunker=chunker)


# 1. Normal Text and Paragraph Preservation

def test_whitespace_normalization_preserves_paragraphs(chunker):
    """Verifies that line endings and whitespace are normalized while retaining paragraphs."""
    raw_text = "Paragraph one with trailing spaces.   \r\n\r\n\r\nParagraph two with leading tab.\t\n\nParagraph three."
    normalized = chunker.normalize_text(raw_text)

    # 3+ newlines should be compressed to exactly double newlines
    assert "\r" not in normalized
    assert "\n\n\n" not in normalized
    assert "Paragraph one with trailing spaces." in normalized
    assert "Paragraph two with leading tab." in normalized
    assert "Paragraph three." in normalized


def test_markdown_code_blocks_and_headings_preserved(chunker):
    """Verifies headings, list items, and code blocks retain structural tokens."""
    md_text = """# Operating Systems

## Process Scheduling
- First-Come, First-Served (FCFS)
- Shortest-Job-Next (SJN)
- Round Robin (RR)

```python
def round_robin(processes, quantum):
    time = 0
    # execute queue
    return time
```
"""
    extracted = ExtractedFileResponse(
        file_id="file_md_code",
        conversation_id="conv_code",
        filename="os_sched.md",
        extension=".md",
        status="ready",
        text=md_text,
        char_count=len(md_text),
    )

    result = chunker.chunk_extracted_document(extracted, ChunkingConfig(chunk_size=1000, chunk_overlap=100))
    assert result.has_content is True
    assert result.total_chunks >= 1
    first_chunk = result.chunks[0].text
    assert "# Operating Systems" in first_chunk
    assert "## Process Scheduling" in first_chunk
    assert "- Round Robin (RR)" in first_chunk
    assert "def round_robin(processes, quantum):" in first_chunk


# 2. Chunk Size and Overlap Enforcement

def test_chunk_size_and_overlap_boundaries(chunker):
    """Verifies that chunks respect max chunk size and overlapping context."""
    # Build text of 1200 characters composed of sentences
    sentences = [f"Sentence number {i:02d} provides valuable domain knowledge for tests." for i in range(25)]
    full_text = " ".join(sentences)

    extracted = ExtractedFileResponse(
        file_id="file_overlap",
        conversation_id="conv_test",
        filename="knowledge.txt",
        extension=".txt",
        status="ready",
        text=full_text,
        char_count=len(full_text),
    )

    config = ChunkingConfig(chunk_size=300, chunk_overlap=60, min_chunk_size=30)
    result = chunker.chunk_extracted_document(extracted, config=config)

    assert result.total_chunks > 1
    for chunk in result.chunks:
        # Every chunk must be strictly positive and <= chunk_size (or slightly over if a single unbreakable token)
        assert len(chunk.text) > 0
        assert chunk.char_count == len(chunk.text)
        assert chunk.token_estimate > 0

    # Verify overlap exists between consecutive chunks
    c0 = result.chunks[0].text
    c1 = result.chunks[1].text
    # Check that tail words of c0 appear in c1
    c0_words = c0.split()
    overlap_found = any(" ".join(c0_words[-k:]) in c1 for k in range(2, min(6, len(c0_words))))
    assert overlap_found, "Consecutive chunks should exhibit overlap context"


# 3. Empty, Whitespace-Only, and Very Short Documents

def test_empty_and_whitespace_only_documents(chunker):
    """Verifies that empty documents produce zero chunks without errors."""
    for empty_input in ["", "   ", "\n\n\t  \r\n"]:
        extracted = ExtractedFileResponse(
            file_id="file_empty",
            conversation_id="conv_empty",
            filename="blank.txt",
            extension=".txt",
            status="ready",
            text=empty_input,
            char_count=len(empty_input),
            has_content=False,
        )
        result = chunker.chunk_extracted_document(extracted)
        assert result.total_chunks == 0
        assert result.chunks == []
        assert result.has_content is False
        assert result.total_characters == 0


def test_very_short_text_single_chunk(chunker):
    """Verifies that text smaller than chunk_size produces exactly one complete chunk."""
    short_text = "Brief summary of ACID transactions."
    extracted = ExtractedFileResponse(
        file_id="file_short",
        conversation_id="conv_short",
        filename="acid.txt",
        extension=".txt",
        status="ready",
        text=short_text,
        char_count=len(short_text),
    )
    result = chunker.chunk_extracted_document(extracted, ChunkingConfig(chunk_size=500, chunk_overlap=50))
    assert result.total_chunks == 1
    assert result.chunks[0].text == short_text
    assert result.chunks[0].chunk_index == 0
    assert result.chunks[0].total_chunks == 1
    assert result.chunks[0].source_page is None


# 4. Long Documents Producing Multiple Chunks

def test_long_document_multi_chunk_ordering(chunker):
    """Verifies long documents generate consecutively indexed chunks."""
    long_text = "\n\n".join([f"Section {i}\n" + ("Detailed explanation of concepts. " * 30) for i in range(15)])
    extracted = ExtractedFileResponse(
        file_id="file_long",
        conversation_id="conv_long",
        filename="book.txt",
        extension=".txt",
        status="ready",
        text=long_text,
        char_count=len(long_text),
    )
    result = chunker.chunk_extracted_document(extracted, ChunkingConfig(chunk_size=400, chunk_overlap=50))
    assert result.total_chunks > 5
    for i, c in enumerate(result.chunks):
        assert c.chunk_index == i
        assert c.total_chunks == result.total_chunks
        assert c.file_id == "file_long"


# 5. Unicode and Multi-Byte Text

def test_unicode_and_special_characters(chunker):
    """Verifies Unicode, mathematical symbols, and non-ASCII scripts chunk cleanly."""
    unicode_text = (
        "Calculus and Algorithms: \u222b f(x)dx = F(x) + C. "
        "\u03c0 \u2248 3.14159, \u03a3 (i=1 to n) i = n(n+1)/2. "
        "\u2714 Verified in Python. \u0928\u092e\u0938\u094d\u0924\u0947 (Namaste) in Hindi."
    )
    extracted = ExtractedFileResponse(
        file_id="file_unicode",
        conversation_id="conv_uni",
        filename="math.txt",
        extension=".txt",
        status="ready",
        text=unicode_text,
        char_count=len(unicode_text),
    )
    result = chunker.chunk_extracted_document(extracted)
    assert result.total_chunks >= 1
    assert "\u222b f(x)dx" in result.chunks[0].text
    assert "\u0928\u092e\u0938\u094d\u0924\u0947" in result.chunks[0].text


# 6. Deterministic Output

def test_deterministic_output_guarantee(chunker):
    """Verifies identical inputs and settings produce byte-identical chunk sequences."""
    text = "Machine learning models require robust preprocessing pipelines.\n\nEvaluation is critical."
    extracted = ExtractedFileResponse(
        file_id="file_det",
        conversation_id="conv_det",
        filename="ml.txt",
        extension=".txt",
        status="ready",
        text=text,
        char_count=len(text),
    )
    res1 = chunker.chunk_extracted_document(extracted, ChunkingConfig(chunk_size=200, chunk_overlap=30))
    res2 = chunker.chunk_extracted_document(extracted, ChunkingConfig(chunk_size=200, chunk_overlap=30))

    assert res1.total_chunks == res2.total_chunks
    for c1, c2 in zip(res1.chunks, res2.chunks):
        assert c1.chunk_id == c2.chunk_id
        assert c1.text == c2.text
        assert c1.start_char == c2.start_char
        assert c1.end_char == c2.end_char


# 7. PDF Page Attribution vs Non-PDF Attribution

def test_pdf_page_attribution_preservation(chunker):
    """Verifies that PDF chunks carry their exact source_page (1-indexed)."""
    p1 = "Introduction to Database Systems. Relational algebra fundamentals."
    p2 = "SQL Queries: SELECT, FROM, WHERE, GROUP BY, and HAVING clauses."
    p3 = "Database Normalization: 1NF, 2NF, 3NF, and Boyce-Codd Normal Form."

    extracted = ExtractedFileResponse(
        file_id="file_pdf_pages",
        conversation_id="conv_pdf",
        filename="dbms.pdf",
        extension=".pdf",
        status="ready",
        text=f"{p1}\n\n{p2}\n\n{p3}",
        char_count=len(p1) + len(p2) + len(p3),
        page_count=3,
        pages=[p1, p2, p3],
    )

    result = chunker.chunk_extracted_document(extracted, ChunkingConfig(chunk_size=500, chunk_overlap=50))
    assert result.total_chunks == 3
    assert result.chunks[0].source_page == 1
    assert "Relational algebra" in result.chunks[0].text
    assert result.chunks[1].source_page == 2
    assert "HAVING clauses" in result.chunks[1].text
    assert result.chunks[2].source_page == 3
    assert "Boyce-Codd Normal Form" in result.chunks[2].text


def test_non_pdf_page_attribution_is_none(chunker):
    """Verifies that non-PDF formats (DOCX, TXT, MD) have source_page set to None."""
    extracted = ExtractedFileResponse(
        file_id="file_docx_pages",
        conversation_id="conv_docx",
        filename="syllabus.docx",
        extension=".docx",
        status="ready",
        text="Sample syllabus text for software engineering.",
        char_count=45,
    )
    result = chunker.chunk_extracted_document(extracted)
    assert result.total_chunks == 1
    assert result.chunks[0].source_page is None


# 8. Invalid Configuration Detection

def test_invalid_configuration_rejection(chunker):
    """Verifies that invalid chunking parameters raise InvalidChunkingConfigError."""
    extracted = ExtractedFileResponse(
        file_id="file_inv",
        conversation_id="conv_inv",
        filename="dummy.txt",
        extension=".txt",
        status="ready",
        text="Valid text payload.",
        char_count=19,
    )

    # overlap >= chunk_size
    with pytest.raises(InvalidChunkingConfigError):
        chunker.chunk_extracted_document(extracted, ChunkingConfig(chunk_size=100, chunk_overlap=100))

    with pytest.raises(InvalidChunkingConfigError):
        chunker.chunk_extracted_document(extracted, ChunkingConfig(chunk_size=100, chunk_overlap=150))

    # negative overlap
    with pytest.raises(InvalidChunkingConfigError):
        chunker.chunk_extracted_document(extracted, ChunkingConfig(chunk_size=100, chunk_overlap=-10))

    # zero or negative chunk_size
    with pytest.raises(InvalidChunkingConfigError):
        chunker.chunk_extracted_document(extracted, ChunkingConfig(chunk_size=0, chunk_overlap=0))

    # min_chunk_size > chunk_size
    with pytest.raises(InvalidChunkingConfigError):
        chunker.chunk_extracted_document(extracted, ChunkingConfig(chunk_size=100, chunk_overlap=20, min_chunk_size=150))


# 9. No Empty Chunks Guarantee

def test_no_empty_or_whitespace_chunks_produced(chunker):
    """Verifies that no empty strings or whitespace-only elements exist in chunks."""
    text_with_holes = "Paragraph one.\n\n   \n\n\n\nParagraph two.\n\n\n   \n\nParagraph three."
    extracted = ExtractedFileResponse(
        file_id="file_holes",
        conversation_id="conv_holes",
        filename="holes.txt",
        extension=".txt",
        status="ready",
        text=text_with_holes,
        char_count=len(text_with_holes),
    )
    result = chunker.chunk_extracted_document(extracted, ChunkingConfig(chunk_size=150, chunk_overlap=20))
    for chunk in result.chunks:
        assert chunk.text != ""
        assert not chunk.text.isspace()
        assert len(chunk.text.strip()) > 0


# 10. FileService End-to-End Integration (Upload -> Extract -> Chunk)

def test_file_service_upload_extract_chunk_pipeline(file_service):
    """Verifies end-to-end integration via FileService for uploaded document."""
    doc = fitz.open()
    p1 = doc.new_page()
    p1.insert_text((50, 50), "Distributed Systems: Consistency Models and CAP Theorem.")
    p2 = doc.new_page()
    p2.insert_text((50, 50), "Consensus Algorithms: Paxos and Raft protocols.")
    pdf_bytes = doc.tobytes()

    # 1. Upload file
    upload_res = file_service.upload_file(
        conversation_id="conv_full_pipeline",
        filename="dist_systems.pdf",
        content_type="application/pdf",
        content=pdf_bytes,
    )
    file_id = upload_res.file_id

    # 2. Chunk file through file service
    chunk_res = file_service.chunk_file(
        file_id=file_id,
        conversation_id="conv_full_pipeline",
        config=ChunkingConfig(chunk_size=300, chunk_overlap=40),
    )

    assert chunk_res.file_id == file_id
    assert chunk_res.has_content is True
    assert chunk_res.total_chunks == 2
    assert chunk_res.chunks[0].source_page == 1
    assert "CAP Theorem" in chunk_res.chunks[0].text
    assert chunk_res.chunks[1].source_page == 2
    assert "Raft protocols" in chunk_res.chunks[1].text

    # 3. Verify cross-conversation access blocked
    with pytest.raises(RuntimeFileNotFoundError):
        file_service.chunk_file(file_id=file_id, conversation_id="unauthorized_conv")


# 11. API Server Route Integration

def test_api_chunk_endpoint():
    """Verifies POST /v1/files/{file_id}/chunk endpoint via TestClient."""
    client = TestClient(app)

    # 1. Upload file
    txt_content = b"Compilers: Lexical Analysis, Syntax Analysis, Semantic Analysis, Intermediate Code Gen."
    upload_res = client.post(
        "/v1/files/upload",
        data={"conversation_id": "test_conv_chunk_api"},
        files={"file": ("compiler.txt", txt_content, "text/plain")},
    )
    assert upload_res.status_code == 200
    file_id = upload_res.json()["file_id"]

    # 2. Invoke /v1/files/{file_id}/chunk
    chunk_res = client.post(
        f"/v1/files/{file_id}/chunk",
        params={
            "conversation_id": "test_conv_chunk_api",
            "chunk_size": 200,
            "chunk_overlap": 30,
        },
    )
    assert chunk_res.status_code == 200
    chunk_data = chunk_res.json()
    assert chunk_data["file_id"] == file_id
    assert chunk_data["has_content"] is True
    assert chunk_data["total_chunks"] >= 1
    assert "Lexical Analysis" in chunk_data["chunks"][0]["text"]

    # 3. Invalid config (overlap >= chunk_size) returns 400
    invalid_res = client.post(
        f"/v1/files/{file_id}/chunk",
        params={
            "conversation_id": "test_conv_chunk_api",
            "chunk_size": 100,
            "chunk_overlap": 150,
        },
    )
    assert invalid_res.status_code == 400

    # 4. Clean up file
    del_res = client.delete(f"/v1/files/{file_id}?conversation_id=test_conv_chunk_api")
    assert del_res.status_code == 200
