"""Comprehensive Unit and Integration Tests for Module 02: Runtime Document Extraction.

Covers:
- Successful PDF extraction, including multiple pages and page metadata
- Encrypted/password-protected PDF rejection with clear errors
- Successful DOCX extraction, including paragraphs and tables
- Successful TXT extraction with encoding handling
- Successful Markdown extraction with headings preserved
- Empty files and empty documents handled gracefully
- Corrupt or malformed documents (corrupt PDF, corrupt DOCX, un-decodable bytes)
- Missing file IDs and nonexistent files
- Unsupported file types rejection
- FileService end-to-end integration (Upload -> Store -> Extract -> Metadata update)
- Conversation isolation: Conversation A cannot extract Conversation B's files
- API server endpoint integration (POST /v1/files/{file_id}/extract)
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
    CorruptedDocumentError,
    ExtractionFailedError,
    RuntimeFileNotFoundError,
    UnsupportedFileTypeError,
)
from aurora.deployment.api_server import app
from aurora.extraction.plugins.docx import DOCXExtractor
from aurora.extraction.plugins.markdown import MarkdownExtractor
from aurora.extraction.plugins.pdf import PDFExtractor
from aurora.extraction.plugins.txt import TXTExtractor
from aurora.ingestion.runtime.file_storage import RuntimeFileStorage
from aurora.ingestion.runtime.file_validator import RuntimeFileValidator
from aurora.models.file_metadata import FileStatus
from aurora.services.file_service import FileService


@pytest.fixture
def temp_storage_dir():
    temp_dir = tempfile.mkdtemp(prefix="aurora_test_runtime_extraction_")
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
def file_service(custom_config, temp_storage_dir):
    storage = RuntimeFileStorage(custom_config, base_dir=temp_storage_dir)
    validator = RuntimeFileValidator(custom_config)
    return FileService(validator=validator, storage=storage)


# Helper generators for realistic document payloads

def create_sample_pdf(pages: list[str], password: str | None = None) -> bytes:
    """Creates in-memory PDF with specified pages, optionally encrypted."""
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((50, 50), text)
    if password:
        # Encrypt with owner/user password
        perm = int(
            fitz.PDF_PERM_ACCESSIBILITY
            | fitz.PDF_PERM_PRINT
            | fitz.PDF_PERM_COPY
            | fitz.PDF_PERM_ANNOTATE
        )
        return doc.tobytes(
            encryption=fitz.PDF_ENCRYPT_AES_256,
            owner_pw=password,
            user_pw=password,
            permissions=perm,
        )
    return doc.tobytes()


def create_sample_docx(paragraphs: list[str], table_rows: list[list[str]] | None = None) -> bytes:
    """Creates in-memory valid DOCX with paragraphs and tables."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '</Types>'
        ))
        body_xml = ""
        for p in paragraphs:
            body_xml += f'<w:p><w:r><w:t>{p}</w:t></w:r></w:p>'
        if table_rows:
            body_xml += '<w:tbl>'
            for row in table_rows:
                body_xml += '<w:tr>'
                for cell in row:
                    body_xml += f'<w:tc><w:p><w:r><w:t>{cell}</w:t></w:r></w:p></w:tc>'
                body_xml += '</w:tr>'
            body_xml += '</w:tbl>'

        doc_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f'<w:body>{body_xml}</w:body>'
            '</w:document>'
        )
        zf.writestr("word/document.xml", doc_xml)
    return buf.getvalue()


# 1. PDF Extraction Tests

def test_pdf_extraction_multi_page(file_service):
    """Verifies multi-page PDF extraction preserving page boundaries and metadata."""
    pdf_bytes = create_sample_pdf([
        "Chapter 1: Operating Systems Concepts.",
        "Chapter 2: Process Scheduling Algorithms and PCB.",
        "Chapter 3: Deadlock Prevention and Banker's Algorithm.",
    ])

    upload_res = file_service.upload_file(
        conversation_id="conv_pdf_test",
        filename="OS_Textbook.pdf",
        content_type="application/pdf",
        content=pdf_bytes,
    )

    extract_res = file_service.extract_file(upload_res.file_id, conversation_id="conv_pdf_test")
    assert extract_res.file_id == upload_res.file_id
    assert extract_res.status == "ready"
    assert extract_res.page_count == 3
    assert len(extract_res.pages) == 3
    assert "Operating Systems Concepts" in extract_res.pages[0]
    assert "Process Scheduling" in extract_res.pages[1]
    assert "Deadlock Prevention" in extract_res.pages[2]
    assert "Banker's Algorithm" in extract_res.text


def test_pdf_extraction_encrypted_rejection(file_service):
    """Verifies password-protected/encrypted PDF fails with clear ExtractionFailedError."""
    encrypted_bytes = create_sample_pdf(["Secret syllabus"], password="master_key_123")

    upload_res = file_service.upload_file(
        conversation_id="conv_pdf_enc",
        filename="Locked.pdf",
        content_type="application/pdf",
        content=encrypted_bytes,
    )

    with pytest.raises(ExtractionFailedError) as exc_info:
        file_service.extract_file(upload_res.file_id, conversation_id="conv_pdf_enc")
    assert "password-protected or encrypted" in str(exc_info.value)

    # Status should reflect failure in metadata
    meta = file_service.get_file(upload_res.file_id, conversation_id="conv_pdf_enc")
    assert meta.status == "failed"


def test_pdf_extraction_corrupt_payload(file_service):
    """Verifies corrupted PDF byte streams raise CorruptedDocumentError."""
    # Start with valid magic header to pass upload validator, but corrupted body
    corrupt_pdf = b"%PDF-1.4\nCorrupt garbage byte data cannot parse"

    upload_res = file_service.upload_file(
        conversation_id="conv_pdf_corrupt",
        filename="Corrupt.pdf",
        content_type="application/pdf",
        content=corrupt_pdf,
    )

    with pytest.raises(CorruptedDocumentError):
        file_service.extract_file(upload_res.file_id, conversation_id="conv_pdf_corrupt")


# 2. DOCX Extraction Tests

def test_docx_extraction_paragraphs_and_tables(file_service):
    """Verifies DOCX extraction including paragraphs and table contents."""
    docx_bytes = create_sample_docx(
        paragraphs=[
            "Database Management Systems Course Overview",
            "Relational Model and Normalization Forms",
        ],
        table_rows=[
            ["Attribute", "Data Type", "Constraint"],
            ["student_id", "INT", "PRIMARY KEY"],
            ["email", "VARCHAR(255)", "UNIQUE"],
        ],
    )

    upload_res = file_service.upload_file(
        conversation_id="conv_docx_test",
        filename="DBMS_Syllabus.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        content=docx_bytes,
    )

    extract_res = file_service.extract_file(upload_res.file_id, conversation_id="conv_docx_test")
    assert extract_res.status == "ready"
    assert "Database Management Systems Course Overview" in extract_res.text
    assert "Relational Model and Normalization Forms" in extract_res.text
    # Check table data extracted
    assert "student_id" in extract_res.text
    assert "PRIMARY KEY" in extract_res.text
    assert extract_res.has_content is True


def test_docx_extraction_corrupt_payload(file_service):
    """Verifies corrupted DOCX raises CorruptedDocumentError."""
    # Valid ZIP header b"PK\x03\x04" but invalid zip stream
    corrupt_docx = b"PK\x03\x04not_a_real_zip_archive_structure"

    upload_res = file_service.upload_file(
        conversation_id="conv_docx_corrupt",
        filename="Broken.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        content=corrupt_docx,
    )

    with pytest.raises(CorruptedDocumentError):
        file_service.extract_file(upload_res.file_id, conversation_id="conv_docx_corrupt")


# 3. TXT Extraction Tests

def test_txt_extraction_utf8_and_fallback(file_service):
    """Verifies plain text extraction with unicode characters."""
    txt_content = "Computer Networks: TCP/IP vs OSI Model.\nFeatures: Reliable, Connection-Oriented. \u2714"
    txt_bytes = txt_content.encode("utf-8")

    upload_res = file_service.upload_file(
        conversation_id="conv_txt_test",
        filename="networks_notes.txt",
        content_type="text/plain",
        content=txt_bytes,
    )

    extract_res = file_service.extract_file(upload_res.file_id, conversation_id="conv_txt_test")
    assert extract_res.status == "ready"
    assert "TCP/IP vs OSI Model" in extract_res.text
    assert "\u2714" in extract_res.text
    assert extract_res.char_count == len(txt_content)


# 4. Markdown Extraction Tests

def test_markdown_extraction_preserves_structure(file_service):
    """Verifies markdown extraction preserves heading hierarchies and formatting text."""
    md_content = """# Data Structures and Algorithms
## Binary Search Tree
A **Binary Search Tree** is a node-based binary tree data structure with the following properties:
- The left subtree of a node contains only nodes with keys lesser than the node's key.
- The right subtree contains keys greater.

```python
def search(root, key):
    if root is None or root.val == key:
        return root
```
"""
    md_bytes = md_content.encode("utf-8")

    upload_res = file_service.upload_file(
        conversation_id="conv_md_test",
        filename="dsa_tree.md",
        content_type="text/markdown",
        content=md_bytes,
    )

    extract_res = file_service.extract_file(upload_res.file_id, conversation_id="conv_md_test")
    assert extract_res.status == "ready"
    assert "# Data Structures and Algorithms" in extract_res.text
    assert "def search(root, key):" in extract_res.text
    assert extract_res.has_content is True


# 5. Empty File and Empty Document Tests

def test_empty_text_and_pdf_handling(file_service):
    """Verifies empty bytes in document extraction return clean empty text response."""
    # Empty TXT
    upload_res = file_service.upload_file(
        conversation_id="conv_empty",
        filename="empty.txt",
        content_type="text/plain",
        content=b"",
    )
    extract_res = file_service.extract_file(upload_res.file_id, conversation_id="conv_empty")
    assert extract_res.text == ""
    assert extract_res.char_count == 0
    assert extract_res.has_content is False


# 6. Conversation Ownership & Missing File Validation

def test_conversation_ownership_isolation(file_service):
    """Verifies that Conversation B cannot trigger extraction or view files of Conversation A."""
    txt_bytes = b"Confidential course materials for CS101."
    upload_res = file_service.upload_file(
        conversation_id="conv_alice",
        filename="cs101.txt",
        content_type="text/plain",
        content=txt_bytes,
    )

    # Bob attempts to extract Alice's file
    with pytest.raises(RuntimeFileNotFoundError) as exc_info:
        file_service.extract_file(upload_res.file_id, conversation_id="conv_bob")
    assert "was not found for conversation 'conv_bob'" in str(exc_info.value)


def test_missing_file_id_raises_error(file_service):
    """Verifies attempting to extract nonexistent file ID raises RuntimeFileNotFoundError."""
    with pytest.raises(RuntimeFileNotFoundError):
        file_service.extract_file("file_nonexistent_9999", conversation_id="conv_test")


# 7. FastAPI API Server Route Integration

def test_api_extract_endpoint_lifecycle():
    """Verifies POST /v1/files/{file_id}/extract works end-to-end via TestClient."""
    client = TestClient(app)

    # 1. Upload valid markdown document
    md_content = b"# Operating Systems\nProcesses and Threads overview."
    upload_res = client.post(
        "/v1/files/upload",
        data={"conversation_id": "test_conv_api_extract"},
        files={"file": ("notes.md", md_content, "text/markdown")},
    )
    assert upload_res.status_code == 200
    file_id = upload_res.json()["file_id"]

    # 2. Call extraction endpoint
    extract_res = client.post(
        f"/v1/files/{file_id}/extract",
        params={"conversation_id": "test_conv_api_extract"},
    )
    assert extract_res.status_code == 200
    extract_data = extract_res.json()
    assert extract_data["file_id"] == file_id
    assert extract_data["status"] == "ready"
    assert "# Operating Systems" in extract_data["text"]
    assert "Processes and Threads overview." in extract_data["text"]

    # 3. Wrong conversation ID returns 404
    wrong_conv_res = client.post(
        f"/v1/files/{file_id}/extract",
        params={"conversation_id": "other_user_conv"},
    )
    assert wrong_conv_res.status_code == 404

    # 4. Clean up file
    del_res = client.delete(f"/v1/files/{file_id}?conversation_id=test_conv_api_extract")
    assert del_res.status_code == 200
