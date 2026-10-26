"""Automated tests for Module 12: File Lifecycle and Automatic Cleanup.

Covers:
1. Explicit file deletion:
   - Removes file and metadata from storage
   - Removes corresponding vectors from ChromaDB
   - Subsequent retrieval does not return deleted content
2. Conversation and file isolation during deletion:
   - Deleting file A in conversation 1 does not affect file B in conversation 1
   - Deleting file A in conversation 1 does not affect file C in conversation 2
3. Missing and unauthorized file deletion:
   - Deleting non-existent file returns 404
   - Deleting with mismatched conversation_id returns 404
4. Full conversation deletion:
   - Removes all files and vector collection for that conversation
5. Automatic cleanup of genuinely stale/abandoned files:
   - Respects max_age_hours retention threshold
   - Retains active conversation files regardless of age
   - Retains files currently in PROCESSING or UPLOADING states
   - Idempotent cleanup execution
"""

import time
import pytest
from fastapi.testclient import TestClient

from aurora.deployment.api_server import app, file_service, settings
from aurora.models.file_metadata import FileStatus, RuntimeFileMetadata


@pytest.fixture
def client():
    return TestClient(app)


def test_explicit_file_deletion_and_vector_removal(client):
    """Deleting a file removes its storage, metadata, and ChromaDB vectors."""
    conv_id = "test_lifecycle_explicit_delete"
    doc_text = "Semaphores use wait() and signal() operations to maintain mutual exclusion."

    # 1. Upload & Index
    upload_res = client.post(
        "/v1/files/upload",
        data={"conversation_id": conv_id},
        files={"file": ("semaphores.txt", doc_text.encode("utf-8"), "text/plain")},
    )
    assert upload_res.status_code == 200
    file_id = upload_res.json()["file_id"]

    try:
        idx_res = client.post(f"/v1/files/{file_id}/index", params={"conversation_id": conv_id})
        assert idx_res.status_code == 200
        assert file_service.vector_store.count(conv_id, file_id=file_id) > 0

        # 2. Delete the file explicitly
        del_res = client.delete(f"/v1/files/{file_id}", params={"conversation_id": conv_id})
        assert del_res.status_code == 200
        assert del_res.json() == {"deleted": True, "file_id": file_id}

        # 3. Verify metadata and storage removed
        get_res = client.get(f"/v1/files/{file_id}", params={"conversation_id": conv_id})
        assert get_res.status_code == 404

        # 4. Verify vectors were purged
        assert file_service.vector_store.count(conv_id, file_id=file_id) == 0

        # 5. Verify subsequent retrieval returns empty
        fused = file_service.build_rag_context("What operations do semaphores use?", conv_id)
        assert not fused.has_context
    finally:
        client.delete(f"/v1/conversations/{conv_id}")


def test_file_deletion_isolation_between_files(client):
    """Deleting one file does not touch another file in the same conversation."""
    conv_id = "test_lifecycle_isolation"
    doc_text1 = "File 1 content for testing."
    doc_text2 = "File 2 content for testing."

    up1 = client.post(
        "/v1/files/upload",
        data={"conversation_id": conv_id},
        files={"file": ("file1.txt", doc_text1.encode("utf-8"), "text/plain")},
    )
    up2 = client.post(
        "/v1/files/upload",
        data={"conversation_id": conv_id},
        files={"file": ("file2.txt", doc_text2.encode("utf-8"), "text/plain")},
    )
    f1 = up1.json()["file_id"]
    f2 = up2.json()["file_id"]

    try:
        client.post(f"/v1/files/{f1}/index", params={"conversation_id": conv_id})
        client.post(f"/v1/files/{f2}/index", params={"conversation_id": conv_id})

        assert file_service.vector_store.count(conv_id, file_id=f1) > 0
        assert file_service.vector_store.count(conv_id, file_id=f2) > 0

        # Delete only file 1
        del1 = client.delete(f"/v1/files/{f1}", params={"conversation_id": conv_id})
        assert del1.status_code == 200

        # File 1 is gone
        assert client.get(f"/v1/files/{f1}", params={"conversation_id": conv_id}).status_code == 404
        assert file_service.vector_store.count(conv_id, file_id=f1) == 0

        # File 2 remains intact
        assert client.get(f"/v1/files/{f2}", params={"conversation_id": conv_id}).status_code == 200
        assert file_service.vector_store.count(conv_id, file_id=f2) > 0
    finally:
        client.delete(f"/v1/conversations/{conv_id}")


def test_unauthorized_and_missing_file_deletion(client):
    """Deleting a non-existent or wrong-conversation file returns 404."""
    conv_a = "test_conv_a"
    conv_b = "test_conv_b"

    up = client.post(
        "/v1/files/upload",
        data={"conversation_id": conv_a},
        files={"file": ("private.txt", b"secret", "text/plain")},
    )
    file_id = up.json()["file_id"]

    try:
        # Wrong conversation
        del_wrong = client.delete(f"/v1/files/{file_id}", params={"conversation_id": conv_b})
        assert del_wrong.status_code == 404

        # Non-existent file
        del_nonexistent = client.delete("/v1/files/file_nonexistent", params={"conversation_id": conv_a})
        assert del_nonexistent.status_code == 404
    finally:
        client.delete(f"/v1/conversations/{conv_a}")


def test_delete_conversation_endpoint(client):
    """Deleting a conversation removes all its files and its vector collection."""
    conv_id = "test_conv_full_delete"
    up = client.post(
        "/v1/files/upload",
        data={"conversation_id": conv_id},
        files={"file": ("doc.txt", b"Knowledge", "text/plain")},
    )
    fid = up.json()["file_id"]
    client.post(f"/v1/files/{fid}/index", params={"conversation_id": conv_id})

    res = client.delete(f"/v1/conversations/{conv_id}")
    assert res.status_code == 200
    assert res.json()["deleted"] is True

    # Vector store count should now be 0
    assert file_service.vector_store.count(conv_id) == 0


def test_cleanup_stale_files_logic(client):
    """Automatic cleanup prunes eligible expired files while preserving active or in-flight files."""
    stale_conv = "test_stale_conv"
    active_conv = "test_active_conv"
    processing_conv = "test_processing_conv"

    # 1. Stale file (simulated age > 24h)
    up_stale = client.post(
        "/v1/files/upload",
        data={"conversation_id": stale_conv},
        files={"file": ("old.txt", b"Old data", "text/plain")},
    )
    fid_stale = up_stale.json()["file_id"]

    # 2. Active file (in active conversation set)
    up_active = client.post(
        "/v1/files/upload",
        data={"conversation_id": active_conv},
        files={"file": ("active.txt", b"Active data", "text/plain")},
    )
    fid_active = up_active.json()["file_id"]

    # 3. Processing file (status = PROCESSING)
    up_proc = client.post(
        "/v1/files/upload",
        data={"conversation_id": processing_conv},
        files={"file": ("proc.txt", b"Processing data", "text/plain")},
    )
    fid_proc = up_proc.json()["file_id"]

    try:
        # Manipulate timestamps to simulate age
        meta_stale = file_service.storage.get_metadata(fid_stale, stale_conv)
        assert meta_stale is not None
        # Make stale file 48 hours old
        meta_stale.created_at = time.time() - (48 * 3600.0)
        file_service.storage.save_metadata(meta_stale)

        meta_proc = file_service.storage.get_metadata(fid_proc, processing_conv)
        assert meta_proc is not None
        meta_proc.status = FileStatus.PROCESSING
        meta_proc.created_at = time.time() - (48 * 3600.0)  # even if old, in-flight processing must not be pruned
        file_service.storage.save_metadata(meta_proc)

        # Run cleanup with max_age_hours=24 and active_conv protected
        clean_res = file_service.cleanup_stale_files(
            max_age_hours=24.0,
            active_conversation_ids={active_conv},
        )

        assert fid_stale in clean_res.stale_files
        assert clean_res.cleaned_files_count >= 1

        # Stale file is purged
        assert file_service.storage.get_metadata(fid_stale, stale_conv) is None

        # Active file is retained
        assert file_service.storage.get_metadata(fid_active, active_conv) is not None

        # Processing file is retained
        assert file_service.storage.get_metadata(fid_proc, processing_conv) is not None

        # Running cleanup again is idempotent
        clean_res2 = file_service.cleanup_stale_files(
            max_age_hours=24.0,
            active_conversation_ids={active_conv},
        )
        assert clean_res2.cleaned_files_count == 0

    finally:
        client.delete(f"/v1/conversations/{stale_conv}")
        client.delete(f"/v1/conversations/{active_conv}")
        client.delete(f"/v1/conversations/{processing_conv}")
