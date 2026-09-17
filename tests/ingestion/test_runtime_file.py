"""Comprehensive Unit and Integration Tests for Module 01: File Upload + Validation.

Covers:
- Valid PDF, DOCX, TXT, MD uploads
- Unsupported extensions rejected (.exe, .py, etc.)
- Oversized file rejection
- Empty filename rejection
- Path traversal sanitization / rejection
- Unique file IDs generated
- Isolated storage location (strict data/runtime_uploads, never data/corpus or data/raw)
- Conversation isolation (Conv A cannot read/delete Conv B files)
- GET existing file / GET nonexistent file
- DELETE existing file / DELETE nonexistent file
- API server endpoints integration via TestClient
"""

import io
import os
import shutil
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aurora.config.settings import RuntimeStorageConfig
from aurora.core.exceptions import (
    FileTooLargeError,
    FileValidationError,
    InvalidConversationIdError,
    InvalidFilenameError,
    RuntimeFileNotFoundError,
    UnsupportedFileTypeError,
)
from aurora.deployment.api_server import app
from aurora.ingestion.runtime.file_storage import RuntimeFileStorage
from aurora.ingestion.runtime.file_validator import RuntimeFileValidator
from aurora.models.file_metadata import FileStatus
from aurora.services.file_service import FileService


@pytest.fixture
def temp_storage_dir():
    temp_dir = tempfile.mkdtemp(prefix="aurora_test_runtime_uploads_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def custom_config():
    return RuntimeStorageConfig(
        upload_dir="data/runtime_uploads",
        max_upload_size_mb=2,  # 2 MB limit for tests
        allowed_extensions=[".pdf", ".docx", ".txt", ".md"],
    )


@pytest.fixture
def validator(custom_config):
    return RuntimeFileValidator(custom_config)


@pytest.fixture
def storage(custom_config, temp_storage_dir):
    return RuntimeFileStorage(config=custom_config, base_dir=temp_storage_dir)


@pytest.fixture
def file_service(validator, storage):
    return FileService(validator=validator, storage=storage)


# ============================================================================
# UNIT TESTS: RuntimeFileValidator
# ============================================================================


def test_valid_pdf_validation(validator):
    validator.validate(
        filename="DBMS_Unit1.pdf",
        content_type="application/pdf",
        size_bytes=1024,
        conversation_id="conv_123",
    )
    # Magic header validation
    validator.validate_stream_header(b"%PDF-1.4 sample content", ".pdf")


def test_valid_docx_validation(validator):
    validator.validate(
        filename="lecture_notes.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        size_bytes=2048,
        conversation_id="conv_123",
    )
    validator.validate_stream_header(b"PK\x03\x04\x14\x00...", ".docx")


def test_valid_txt_validation(validator):
    validator.validate(
        filename="syllabus.txt",
        content_type="text/plain",
        size_bytes=512,
        conversation_id="conv_123",
    )


def test_valid_md_validation(validator):
    validator.validate(
        filename="readme.md",
        content_type="text/markdown",
        size_bytes=256,
        conversation_id="conv_123",
    )


def test_unsupported_extension_rejected(validator):
    with pytest.raises(UnsupportedFileTypeError):
        validator.validate(
            filename="malicious.exe",
            content_type="application/x-msdownload",
            size_bytes=100,
            conversation_id="conv_123",
        )

    with pytest.raises(UnsupportedFileTypeError):
        validator.validate(
            filename="script.py",
            content_type="text/x-python",
            size_bytes=100,
            conversation_id="conv_123",
        )


def test_oversized_file_rejected(validator):
    # Config is 2 MB max = 2,097,152 bytes
    oversized_bytes = 3 * 1024 * 1024
    with pytest.raises(FileTooLargeError):
        validator.validate(
            filename="big_book.pdf",
            content_type="application/pdf",
            size_bytes=oversized_bytes,
            conversation_id="conv_123",
        )


def test_empty_filename_rejected(validator):
    with pytest.raises(InvalidFilenameError):
        validator.validate(
            filename="",
            content_type="application/pdf",
            size_bytes=100,
            conversation_id="conv_123",
        )

    with pytest.raises(InvalidFilenameError):
        validator.validate(
            filename="   ",
            content_type="application/pdf",
            size_bytes=100,
            conversation_id="conv_123",
        )


def test_path_traversal_filename_rejected_or_sanitized(validator):
    with pytest.raises(InvalidFilenameError):
        validator.validate(
            filename="../../etc/passwd",
            content_type="text/plain",
            size_bytes=100,
            conversation_id="conv_123",
        )


def test_invalid_conversation_id_rejected(validator):
    with pytest.raises(InvalidConversationIdError):
        validator.validate(
            filename="test.txt",
            content_type="text/plain",
            size_bytes=100,
            conversation_id="../traversal",
        )

    with pytest.raises(InvalidConversationIdError):
        validator.validate(
            filename="test.txt",
            content_type="text/plain",
            size_bytes=100,
            conversation_id="",
        )


def test_mismatched_binary_header_rejected(validator):
    with pytest.raises(UnsupportedFileTypeError):
        validator.validate_stream_header(b"NOT_A_PDF_HEADER", ".pdf")


# ============================================================================
# INTEGRATION TESTS: FileService & Storage Isolation
# ============================================================================


def test_file_service_upload_success(file_service, temp_storage_dir):
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    response = file_service.upload_file(
        conversation_id="conv_alpha",
        filename="DBMS_Unit3.pdf",
        content_type="application/pdf",
        content=pdf_bytes,
    )

    assert response.file_id.startswith("file_")
    assert response.conversation_id == "conv_alpha"
    assert response.filename == "DBMS_Unit3.pdf"
    assert response.extension == ".pdf"
    assert response.size_bytes == len(pdf_bytes)
    assert response.status == "stored"

    # Verify physical storage location
    expected_dir = temp_storage_dir / "conv_alpha" / response.file_id
    assert expected_dir.exists()
    assert (expected_dir / "original_file.pdf").is_file()
    assert (expected_dir / "metadata.json").is_file()

    # Verify NOT in protected corpus or raw data directories
    assert "data/corpus" not in str(expected_dir)
    assert "data/raw" not in str(expected_dir)


def test_unique_file_ids(file_service):
    content = b"Simple text"
    res1 = file_service.upload_file(
        conversation_id="conv_1",
        filename="doc1.txt",
        content_type="text/plain",
        content=content,
    )
    res2 = file_service.upload_file(
        conversation_id="conv_1",
        filename="doc2.txt",
        content_type="text/plain",
        content=content,
    )
    assert res1.file_id != res2.file_id


def test_conversation_isolation(file_service):
    content = b"Syllabus notes"
    res_a = file_service.upload_file(
        conversation_id="conv_A",
        filename="file_a.txt",
        content_type="text/plain",
        content=content,
    )

    # Conversation A can access its file
    meta_a = file_service.get_file(res_a.file_id, conversation_id="conv_A")
    assert meta_a.file_id == res_a.file_id

    # Conversation B CANNOT access Conversation A's file
    with pytest.raises(RuntimeFileNotFoundError):
        file_service.get_file(res_a.file_id, conversation_id="conv_B")

    # Conversation B CANNOT delete Conversation A's file
    with pytest.raises(RuntimeFileNotFoundError):
        file_service.delete_file(res_a.file_id, conversation_id="conv_B")

    # Conversation A can delete its file
    assert file_service.delete_file(res_a.file_id, conversation_id="conv_A") is True


def test_get_and_delete_nonexistent_file(file_service):
    with pytest.raises(RuntimeFileNotFoundError):
        file_service.get_file("file_nonexistent_999")

    with pytest.raises(RuntimeFileNotFoundError):
        file_service.delete_file("file_nonexistent_999")


# ============================================================================
# FASTAPI ENDPOINT TESTS
# ============================================================================


def test_api_upload_get_and_delete_lifecycle():
    client = TestClient(app)

    # 1. Upload valid PDF
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    upload_res = client.post(
        "/v1/files/upload",
        data={"conversation_id": "test_conv_api"},
        files={"file": ("OperatingSystems.pdf", io.BytesIO(pdf_content), "application/pdf")},
    )
    assert upload_res.status_code == 200
    upload_data = upload_res.json()
    assert upload_data["status"] == "stored"
    assert upload_data["filename"] == "OperatingSystems.pdf"
    assert upload_data["conversation_id"] == "test_conv_api"
    file_id = upload_data["file_id"]

    # 2. Get file metadata
    get_res = client.get(f"/v1/files/{file_id}", params={"conversation_id": "test_conv_api"})
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["file_id"] == file_id
    assert "storage_path" not in get_data  # Internal path never exposed to client

    # 3. Isolation: query with wrong conversation_id yields 404
    wrong_conv_res = client.get(f"/v1/files/{file_id}", params={"conversation_id": "other_conv"})
    assert wrong_conv_res.status_code == 404

    # 4. Delete file
    del_res = client.delete(f"/v1/files/{file_id}", params={"conversation_id": "test_conv_api"})
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True

    # 5. Verify file is gone
    get_after_del = client.get(f"/v1/files/{file_id}")
    assert get_after_del.status_code == 404


def test_api_upload_validation_failure():
    client = TestClient(app)

    # Unsupported extension (.exe)
    res = client.post(
        "/v1/files/upload",
        data={"conversation_id": "test_conv_api"},
        files={"file": ("virus.exe", io.BytesIO(b"malicious code"), "application/octet-stream")},
    )
    assert res.status_code == 400
    assert "not supported" in res.json()["detail"].lower()

    # Missing conversation_id
    res_no_conv = client.post(
        "/v1/files/upload",
        data={},
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert res_no_conv.status_code in [400, 422]
