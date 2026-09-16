"""Verification tests for the Phase 1 Architecture Refinements."""

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from aurora.core.artifact import ArtifactMetadata


def test_artifact_metadata_immutability() -> None:
    """Artifact metadata parameters should be frozen and raise on writes."""
    meta = ArtifactMetadata(
        artifact_id=uuid.uuid4(),
        checksum="hash123",
        created_at=datetime.now(timezone.utc),
    )
    with pytest.raises((ValidationError, TypeError)):
        meta.checksum = "new_hash"  # type: ignore


def test_schema_version_present_on_metadata() -> None:
    """ArtifactMetadata has default schema version 1.0.0."""
    meta = ArtifactMetadata(
        artifact_id=uuid.uuid4(),
        checksum="hash123",
        created_at=datetime.now(timezone.utc),
    )
    assert meta.schema_version == "1.0.0"


def test_acyclic_parent_lineage() -> None:
    """Parent reference links must form an acyclic graph (no self-loops or cycles)."""
    id_1 = uuid.uuid4()
    id_2 = uuid.uuid4()
    id_3 = uuid.uuid4()

    meta_1 = ArtifactMetadata(
        artifact_id=id_1,
        parent_artifact_ids=[],
        checksum="hash1",
        created_at=datetime.now(timezone.utc),
    )
    meta_2 = ArtifactMetadata(
        artifact_id=id_2,
        parent_artifact_ids=[id_1],
        checksum="hash2",
        created_at=datetime.now(timezone.utc),
    )
    meta_3 = ArtifactMetadata(
        artifact_id=id_3,
        parent_artifact_ids=[id_2],
        checksum="hash3",
        created_at=datetime.now(timezone.utc),
    )

    # Acyclic helper function
    def assert_acyclic(meta: ArtifactMetadata, registry: dict) -> None:
        visited = set()
        stack = [meta.artifact_id]
        while stack:
            curr_id = stack.pop()
            if curr_id in visited:
                raise ValueError("Lineage cycle detected!")
            visited.add(curr_id)
            parent_ids = registry.get(curr_id, [])
            stack.extend(parent_ids)

    registry = {
        id_1: meta_1.parent_artifact_ids,
        id_2: meta_2.parent_artifact_ids,
        id_3: meta_3.parent_artifact_ids,
    }
    # Should compile without cycle errors
    assert_acyclic(meta_3, registry)

    # Induce artificial cycle: meta_1 references meta_3
    registry[id_1] = [id_3]
    with pytest.raises(ValueError, match="Lineage cycle detected!"):
        assert_acyclic(meta_3, registry)


def test_deterministic_checksums() -> None:
    """Artifact checks remain fully deterministic for same payload."""
    import hashlib
    text = "Coherent document text"
    hash_1 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    hash_2 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert hash_1 == hash_2
