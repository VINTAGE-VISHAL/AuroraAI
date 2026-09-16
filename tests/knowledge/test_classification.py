"""Unit tests for the Knowledge Unit Classification Subsystem."""

import uuid
from datetime import datetime, timezone

from aurora.core.pipeline import PipelineContext
from aurora.knowledge.classification.pipeline import KnowledgeUnitClassifierPipeline
from aurora.models import (
    ArtifactMetadata,
    Concept,
    DocumentSegment,
    ExtractedConceptCollection,
    FrameworkInfo,
    KnowledgeType,
    PipelineProvenance,
    StructuredDocument,
)
from aurora.models.enums import DocumentState, SegmentType
from aurora.models.metadata import FileMetadata


def test_classification_pipeline_execution() -> None:
    """Verify Candidate Discovery, Type Classification, and Concept Association."""
    pipeline = KnowledgeUnitClassifierPipeline()
    context = PipelineContext()

    provenance = PipelineProvenance(
        stage=DocumentState.SEGMENTED,
        producer="test",
        timestamp=datetime.now(timezone.utc),
        framework=FrameworkInfo(module_name="test", module_version="0.1"),
    )
    artifact = ArtifactMetadata(
        artifact_id=uuid.uuid4(),
        checksum="hash_doc",
        created_at=provenance.timestamp,
    )

    concepts = [
        Concept(
            concept_id=uuid.uuid5(uuid.NAMESPACE_DNS, "normalization"),
            canonical_name="Normalization",
            aliases=[],
            subject="Databases",
            difficulty="intermediate",
        ),
        Concept(
            concept_id=uuid.uuid5(uuid.NAMESPACE_DNS, "boyce-codd normal form"),
            canonical_name="Boyce-Codd Normal Form",
            aliases=["BCNF"],
            subject="Databases",
            difficulty="advanced",
        ),
    ]

    concept_col = ExtractedConceptCollection(
        collection_id=uuid.uuid4(),
        source_document_id="doc123",
        concepts=concepts,
        taxonomy_version="1.0.0",
        pipeline_version="1.0.0",
        artifact=artifact,
    )

    segments = [
        DocumentSegment(
            segment_id="seg1",
            doc_id="doc123",
            type=SegmentType.PARAGRAPH,
            text="Definition: Normalization is a design process.",
            start_offset=0,
            end_offset=46,
            segment_index=0,
            provenance=provenance,
        ),
        DocumentSegment(
            segment_id="seg2",
            doc_id="doc123",
            type=SegmentType.PARAGRAPH,
            text="Example: Boyce-Codd Normal Form avoids redundancy.",
            start_offset=47,
            end_offset=97,
            segment_index=1,
            provenance=provenance,
        ),
    ]

    doc = StructuredDocument(
        doc_id="doc123",
        segments=segments,
        metadata=FileMetadata(source_path="db.txt", file_type="txt", char_count=98),
        provenance=provenance,
        artifact=artifact,
    )

    res = pipeline.execute((concept_col, doc), context)
    col = res.result

    assert len(col.units) == 2
    assert len(col.mappings) == 2

    # Check unit type classification
    unit1 = next(u for u in col.units if u.content.startswith("Definition:"))
    assert unit1.type == KnowledgeType.DEFINITION

    unit2 = next(u for u in col.units if u.content.startswith("Example:"))
    assert unit2.type == KnowledgeType.EXAMPLE


def test_shared_knowledge_unit_mapping() -> None:
    """Verify that multiple concept mentions in one segment are mapped correctly."""
    pipeline = KnowledgeUnitClassifierPipeline()
    context = PipelineContext()

    provenance = PipelineProvenance(
        stage=DocumentState.SEGMENTED,
        producer="test",
        timestamp=datetime.now(timezone.utc),
        framework=FrameworkInfo(module_name="test", module_version="0.1"),
    )
    artifact = ArtifactMetadata(
        artifact_id=uuid.uuid4(),
        checksum="hash_doc",
        created_at=provenance.timestamp,
    )

    concepts = [
        Concept(
            concept_id=uuid.uuid5(uuid.NAMESPACE_DNS, "normalization"),
            canonical_name="Normalization",
            aliases=[],
            subject="Databases",
            difficulty="intermediate",
        ),
        Concept(
            concept_id=uuid.uuid5(uuid.NAMESPACE_DNS, "boyce-codd normal form"),
            canonical_name="Boyce-Codd Normal Form",
            aliases=["BCNF"],
            subject="Databases",
            difficulty="advanced",
        ),
    ]

    concept_col = ExtractedConceptCollection(
        collection_id=uuid.uuid4(),
        source_document_id="doc123",
        concepts=concepts,
        taxonomy_version="1.0.0",
        pipeline_version="1.0.0",
        artifact=artifact,
    )

    # Segment contains mentions of BOTH concepts
    segments = [
        DocumentSegment(
            segment_id="seg1",
            doc_id="doc123",
            type=SegmentType.PARAGRAPH,
            text="Definition: BCNF is a Boyce-Codd Normal Form that extends Normalization rules.",
            start_offset=0,
            end_offset=79,
            segment_index=0,
            provenance=provenance,
        )
    ]

    doc = StructuredDocument(
        doc_id="doc123",
        segments=segments,
        metadata=FileMetadata(source_path="db.txt", file_type="txt", char_count=79),
        provenance=provenance,
        artifact=artifact,
    )

    res = pipeline.execute((concept_col, doc), context)
    col = res.result

    # One unit created
    assert len(col.units) == 1
    # Two mappings constructed (one for Normalization, one for Boyce-Codd Normal Form)
    assert len(col.mappings) == 2
    # Two occurrences registered
    assert {occ.matched_text for occ in col.occurrences} == {
        "Normalization", "Boyce-Codd Normal Form"
    }
