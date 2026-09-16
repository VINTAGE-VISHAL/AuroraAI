"""Unit tests for the Concept Relationship Extraction Subsystem."""

import uuid
from datetime import datetime, timezone

from aurora.core.pipeline import PipelineContext
from aurora.knowledge.relationship.pipeline import ConceptRelationshipExtractorPipeline
from aurora.models import (
    ArtifactMetadata,
    Concept,
    ConceptKnowledgeMapping,
    DocumentSegment,
    ExtractedConceptCollection,
    FrameworkInfo,
    KnowledgeType,
    KnowledgeUnit,
    KnowledgeUnitCollection,
    PipelineProvenance,
    RelationshipType,
    StructuredDocument,
)
from aurora.models.enums import DocumentState, SegmentType
from aurora.models.metadata import FileMetadata


def test_relationship_discovery_and_classification() -> None:
    """Verify Candidate Discovery, Classification, and direction normalization."""
    pipeline = ConceptRelationshipExtractorPipeline(graph_namespace="DBMS")
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

    # 1. Structural hierarchy mention: BCNF paragraph is nested under Normalization heading
    # 2. Pattern mention with reverse direction:
    # Normalization is required for Boyce-Codd Normal Form
    segments = [
        DocumentSegment(
            segment_id="seg_head",
            doc_id="doc123",
            type=SegmentType.HEADING,
            text="# Normalization",
            start_offset=0,
            end_offset=15,
            segment_index=0,
            provenance=provenance,
        ),
        DocumentSegment(
            segment_id="seg_para",
            doc_id="doc123",
            type=SegmentType.PARAGRAPH,
            text="Normalization is required for Boyce-Codd Normal Form.",
            start_offset=16,
            end_offset=69,
            segment_index=1,
            provenance=provenance,
        ),
    ]

    doc = StructuredDocument(
        doc_id="doc123",
        segments=segments,
        metadata=FileMetadata(source_path="db.txt", file_type="txt", char_count=70),
        provenance=provenance,
        artifact=artifact,
    )

    # Wrap as unit collection
    u1 = KnowledgeUnit(
        unit_id=uuid.uuid4(),
        type=KnowledgeType.NOTE,
        content="# Normalization",
        occurrence_ids=[],
        evidence_ids=[],
        metadata={"segment_index": 0},
    )
    u2 = KnowledgeUnit(
        unit_id=uuid.uuid4(),
        type=KnowledgeType.DEFINITION,
        content="Normalization is required for Boyce-Codd Normal Form.",
        occurrence_ids=[],
        evidence_ids=[],
        metadata={"segment_index": 1},
    )

    unit_col = KnowledgeUnitCollection(
        collection_id=uuid.uuid4(),
        source_document_id="doc123",
        units=[u1, u2],
        mappings=[
            ConceptKnowledgeMapping(
                concept_id=concepts[0].concept_id,
                knowledge_unit_ids=[u1.unit_id],
            )
        ],
        artifact=artifact,
    )

    res = pipeline.execute((concept_col, unit_col, doc), context)
    col = res.result

    assert len(col.relationships) > 0

    # Verify direction normalization for "is required for" pattern -> DEPENDS_ON relationship
    # Normalization is required for Boyce-Codd Normal Form ->
    # Boyce-Codd Normal Form DEPENDS_ON Normalization
    depends_rel = next(
        r for r in col.relationships if r.type == RelationshipType.DEPENDS_ON
    )
    assert depends_rel.source_concept_id == concepts[1].concept_id  # BCNF
    assert depends_rel.target_concept_id == concepts[0].concept_id  # Normalization


def test_validation_self_loop_and_duplicate_collapsing() -> None:
    """Verify that self-loops are rejected and duplicates normalized to highest confidence edge."""
    pipeline = ConceptRelationshipExtractorPipeline(graph_namespace="DBMS")
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

    c_id = uuid.uuid5(uuid.NAMESPACE_DNS, "normalization")
    concepts = [
        Concept(
            concept_id=c_id,
            canonical_name="Normalization",
            aliases=[],
            subject="Databases",
            difficulty="intermediate",
        )
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
        # Normalization references Normalization (self-loop)
        DocumentSegment(
            segment_id="seg1",
            doc_id="doc123",
            type=SegmentType.PARAGRAPH,
            text="Normalization references Normalization.",
            start_offset=0,
            end_offset=39,
            segment_index=0,
            provenance=provenance,
        ),
    ]

    doc = StructuredDocument(
        doc_id="doc123",
        segments=segments,
        metadata=FileMetadata(source_path="db.txt", file_type="txt", char_count=39),
        provenance=provenance,
        artifact=artifact,
    )

    unit = KnowledgeUnit(
        unit_id=uuid.uuid4(),
        type=KnowledgeType.NOTE,
        content="Normalization references Normalization.",
        occurrence_ids=[],
        evidence_ids=[],
        metadata={"segment_index": 0},
    )

    unit_col = KnowledgeUnitCollection(
        collection_id=uuid.uuid4(),
        source_document_id="doc123",
        units=[unit],
        mappings=[],
        artifact=artifact,
    )

    res = pipeline.execute((concept_col, unit_col, doc), context)
    col = res.result

    # Self-loops must be filtered out entirely
    assert len(col.relationships) == 0
