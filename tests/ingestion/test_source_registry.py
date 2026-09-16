"""Unit tests for FileScanner and SourceRegistry."""

from pathlib import Path

import pytest

from aurora.core.exceptions import InvalidSourceError, SourceNotFoundError
from aurora.ingestion.file_scanner import FileScanner
from aurora.ingestion.source_registry import SourceRegistry
from aurora.models.source import DocumentChange, SourceStatus


def test_empty_directory_scan(tmp_path: Path) -> None:
    """Scan empty directory and check that it returns empty list of changes."""
    scanner = FileScanner()
    registry = SourceRegistry()
    changes = registry.refresh(scanner, str(tmp_path), {".pdf"})
    assert len(changes) == 0
    assert len(registry.list_documents()) == 0


def test_missing_directory_scan() -> None:
    """Scan a non-existent directory and ensure InvalidSourceError is raised."""
    scanner = FileScanner()
    registry = SourceRegistry()
    with pytest.raises(InvalidSourceError):
        registry.refresh(scanner, "non/existent/path/dir", {".pdf"})


def test_basic_registration(tmp_path: Path) -> None:
    """Register files and check status is ACTIVE."""
    scanner = FileScanner()
    registry = SourceRegistry()

    # Create test subject directory and file
    math_dir = tmp_path / "math"
    math_dir.mkdir()
    file_path = math_dir / "algebra.pdf"
    file_path.write_text("algebra rules")

    changes = registry.refresh(scanner, str(tmp_path), {".pdf"})
    assert changes == [DocumentChange.NEW]

    docs = registry.list_documents()
    assert len(docs) == 1
    assert docs[0].subject_name == "math"
    assert docs[0].metadata.status == SourceStatus.ACTIVE

    doc = registry.get_document(docs[0].doc_id)
    assert doc.uri == file_path.resolve().as_uri()


def test_case_insensitive_extensions(tmp_path: Path) -> None:
    """Supported extensions should be filtered case-insensitively."""
    scanner = FileScanner()
    registry = SourceRegistry()

    f1 = tmp_path / "doc1.PDF"
    f1.write_text("pdf 1")
    f2 = tmp_path / "doc2.pDf"
    f2.write_text("pdf 2")
    f3 = tmp_path / "doc3.txt"
    f3.write_text("text")

    changes = registry.refresh(scanner, str(tmp_path), {".pdf"})
    assert len(changes) == 2
    assert len(registry.list_documents()) == 2


def test_duplicate_filenames_different_folders(tmp_path: Path) -> None:
    """Duplicate filenames in different folders get unique stable IDs."""
    scanner = FileScanner()
    registry = SourceRegistry()

    d1 = tmp_path / "math"
    d1.mkdir()
    (d1 / "intro.pdf").write_text("math intro")

    d2 = tmp_path / "physics"
    d2.mkdir()
    (d2 / "intro.pdf").write_text("physics intro")

    registry.refresh(scanner, str(tmp_path), {".pdf"})
    docs = registry.list_documents()
    assert len(docs) == 2
    ids = {doc.doc_id for doc in docs}
    assert len(ids) == 2


def test_hidden_files_ignored(tmp_path: Path) -> None:
    """Files starting with dot should be ignored."""
    scanner = FileScanner()
    registry = SourceRegistry()

    f1 = tmp_path / "visible.pdf"
    f1.write_text("content")
    f2 = tmp_path / ".hidden.pdf"
    f2.write_text("secret")

    registry.refresh(scanner, str(tmp_path), {".pdf"})
    assert len(registry.list_documents()) == 1


def test_recursive_scanning(tmp_path: Path) -> None:
    """Nested directories should be traversed fully."""
    scanner = FileScanner()
    registry = SourceRegistry()

    d1 = tmp_path / "level1" / "level2"
    d1.mkdir(parents=True)
    (d1 / "nested.pdf").write_text("nested content")

    registry.refresh(scanner, str(tmp_path), {".pdf"})
    assert len(registry.list_documents()) == 1


def test_unicode_filenames(tmp_path: Path) -> None:
    """Unicode filenames must scan and parse without throwing."""
    scanner = FileScanner()
    registry = SourceRegistry()

    f1 = tmp_path / "math_数学.pdf"
    f1.write_text("unicode content")

    changes = registry.refresh(scanner, str(tmp_path), {".pdf"})
    assert changes == [DocumentChange.NEW]
    assert len(registry.list_documents()) == 1


def test_metadata_refresh_unchanged(tmp_path: Path) -> None:
    """Unchanged content returns UNCHANGED status on second refresh."""
    scanner = FileScanner()
    registry = SourceRegistry()

    f1 = tmp_path / "doc.pdf"
    f1.write_text("content")

    changes1 = registry.refresh(scanner, str(tmp_path), {".pdf"})
    assert changes1 == [DocumentChange.NEW]

    changes2 = registry.refresh(scanner, str(tmp_path), {".pdf"})
    assert changes2 == [DocumentChange.UNCHANGED]


def test_metadata_refresh_modified(tmp_path: Path) -> None:
    """Altered content changes checksum and increments version."""
    scanner = FileScanner()
    registry = SourceRegistry()

    f1 = tmp_path / "doc.pdf"
    f1.write_text("original content")

    registry.refresh(scanner, str(tmp_path), {".pdf"})
    doc = registry.list_documents()[0]
    assert doc.metadata.version == 1
    assert doc.metadata.status == SourceStatus.ACTIVE

    # modify content
    f1.write_text("modified content")
    changes = registry.refresh(scanner, str(tmp_path), {".pdf"})
    assert changes == [DocumentChange.MODIFIED]

    doc_mod = registry.list_documents()[0]
    assert doc_mod.metadata.version == 2
    assert doc_mod.metadata.status == SourceStatus.MODIFIED


def test_document_removal(tmp_path: Path) -> None:
    """Deleted file returns REMOVED state and is omitted from active list."""
    scanner = FileScanner()
    registry = SourceRegistry()

    f1 = tmp_path / "doc.pdf"
    f1.write_text("content")

    registry.refresh(scanner, str(tmp_path), {".pdf"})
    assert len(registry.list_documents()) == 1

    # delete file
    f1.unlink()
    changes = registry.refresh(scanner, str(tmp_path), {".pdf"})
    assert changes == [DocumentChange.REMOVED]
    assert len(registry.list_documents()) == 0

    with pytest.raises(SourceNotFoundError):
        # Querying removed doc throws exception
        registry.get_document("any_doc_id_would_fail")


def test_subject_discovery(tmp_path: Path) -> None:
    """List subjects dynamically based on subject folders."""
    scanner = FileScanner()
    registry = SourceRegistry()

    (tmp_path / "algebra").mkdir()
    (tmp_path / "algebra" / "doc.pdf").write_text("math")

    (tmp_path / "mechanics").mkdir()
    (tmp_path / "mechanics" / "doc.pdf").write_text("physics")

    registry.refresh(scanner, str(tmp_path), {".pdf"})
    subjects = registry.list_subjects()
    assert subjects == ["algebra", "mechanics"]

    docs = registry.get_documents_by_subject("algebra")
    assert len(docs) == 1
    assert docs[0].subject_name == "algebra"


def test_permission_denied_raises_invalid_source(tmp_path: Path) -> None:
    """Accessing unreadable files should raise InvalidSourceError."""
    scanner = FileScanner()
    registry = SourceRegistry()

    unreadable = tmp_path / "locked.pdf"
    unreadable.write_text("locked")

    from unittest.mock import patch
    with patch("builtins.open", side_effect=PermissionError("Permission Denied")):
        with pytest.raises(InvalidSourceError):
            registry.refresh(scanner, str(tmp_path), {".pdf"})

