"""Unit tests for the Concept Extraction Subsystem."""

import uuid
from datetime import datetime, timezone

import pytest

from aurora.core.pipeline import PipelineContext
from aurora.knowledge.extraction.pipeline import ConceptExtractorPipeline
from aurora.models import (
    ArtifactMetadata,
    DocumentSegment,
    FrameworkInfo,
    PipelineProvenance,
    StructuredDocument,
)
from aurora.models.enums import DocumentState, SegmentType
from aurora.models.metadata import FileMetadata


@pytest.fixture
def sample_structured_doc() -> StructuredDocument:
    """Fixture returning a sample StructuredDocument with concepts inside segments."""
    meta = FileMetadata(source_path="dbms.txt", file_type="txt", char_count=200)
    framework = FrameworkInfo(module_name="test", module_version="0.1")
    provenance = PipelineProvenance(
        stage=DocumentState.SEGMENTED,
        producer="test",
        timestamp=datetime.now(timezone.utc),
        framework=framework,
    )
    artifact = ArtifactMetadata(
        artifact_id=uuid.uuid4(),
        checksum="hash_doc",
        created_at=provenance.timestamp,
    )

    # Segments containing headings, bold text, and definition prefixes
    segments = [
        DocumentSegment(
            segment_id="1",
            doc_id="dbms_doc",
            type=SegmentType.HEADING,
            text="# Database Normalization",
            start_offset=0,
            end_offset=24,
            segment_index=0,
            provenance=provenance,
        ),
        DocumentSegment(
            segment_id="2",
            doc_id="dbms_doc",
            type=SegmentType.PARAGRAPH,
            text="We will discuss **Boyce-Codd Normal Form** or BCNF.",
            start_offset=25,
            end_offset=75,
            segment_index=1,
            provenance=provenance,
        ),
        DocumentSegment(
            segment_id="3",
            doc_id="dbms_doc",
            type=SegmentType.PARAGRAPH,
            text="Definition: DBMS. DBMS is a database system.",
            start_offset=76,
            end_offset=120,
            segment_index=2,
            provenance=provenance,
        ),
        # Noise to test false-positive protection
        DocumentSegment(
            segment_id="4",
            doc_id="dbms_doc",
            type=SegmentType.HEADING,
            text="## Figure 1.2 Chart",
            start_offset=104,
            end_offset=123,
            segment_index=3,
            provenance=provenance,
        ),
        DocumentSegment(
            segment_id="5",
            doc_id="dbms_doc",
            type=SegmentType.PARAGRAPH,
            text="Refer to **Table 3** on page 45.",
            start_offset=124,
            end_offset=156,
            segment_index=4,
            provenance=provenance,
        ),
    ]

    return StructuredDocument(
        doc_id="dbms_doc",
        segments=segments,
        metadata=meta,
        provenance=provenance,
        artifact=artifact,
    )


def test_concept_extraction_pipeline_execution(sample_structured_doc: StructuredDocument) -> None:
    """Verify candidate discovery, normalization, validation, and assembly."""
    pipeline = ConceptExtractorPipeline()
    context = PipelineContext()

    res = pipeline.execute(sample_structured_doc, context)
    collection = res.result

    assert len(collection.concepts) == 3

    # Check normalization: DBMS -> Database Management System
    names = {c.canonical_name for c in collection.concepts}
    assert "Database Normalization" in names
    assert "Boyce-Codd Normal Form" in names
    assert "Database Management System" in names

    # Check alias mapping reverse lookup
    bcnf_concept = next(
        c for c in collection.concepts if c.canonical_name == "Boyce-Codd Normal Form"
    )
    assert "BCNF" in bcnf_concept.aliases

    dbms_concept = next(
        c for c in collection.concepts if c.canonical_name == "Database Management System"
    )
    assert "DBMS" in dbms_concept.aliases


def test_false_positive_noise_protection(sample_structured_doc: StructuredDocument) -> None:
    """Ensure headings like Figure/Table and bold tags containing Table 3 are ignored."""
    pipeline = ConceptExtractorPipeline()
    context = PipelineContext()

    res = pipeline.execute(sample_structured_doc, context)
    collection = res.result

    names = {c.canonical_name for c in collection.concepts}
    assert "Figure 1.2 Chart" not in names
    assert "Table 3" not in names
    assert "Chart" not in names


def test_extraction_determinism_and_empty_handling(
    sample_structured_doc: StructuredDocument
) -> None:
    """Ensure identical runs produce identical checksums/IDs, and empty docs handle cleanly."""
    pipeline = ConceptExtractorPipeline()
    context1 = PipelineContext()
    context2 = PipelineContext()

    res1 = pipeline.execute(sample_structured_doc, context1).result
    res2 = pipeline.execute(sample_structured_doc, context2).result

    assert res1.collection_id != res2.collection_id  # UUIDs are unique per run
    assert res1.artifact.checksum == res2.artifact.checksum
    assert [c.concept_id for c in res1.concepts] == [c.concept_id for c in res2.concepts]

    # Empty document case
    empty_doc = StructuredDocument(
        doc_id="empty_doc",
        segments=[],
        metadata=sample_structured_doc.metadata,
        provenance=sample_structured_doc.provenance,
        artifact=sample_structured_doc.artifact,
    )
    res_empty = pipeline.execute(empty_doc, context1).result
    assert len(res_empty.concepts) == 0
