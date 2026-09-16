"""Unit tests for the Semantic Chunk Builder Subsystem."""

import uuid
from datetime import datetime, timezone

from aurora.core.pipeline import PipelineContext
from aurora.knowledge.chunk.pipeline import SemanticChunkBuilderPipeline
from aurora.models import (
    ArtifactMetadata,
    Concept,
    ConceptKnowledgeMapping,
    ConceptRelationship,
    GraphStatistics,
    KnowledgeGraph,
    KnowledgeType,
    KnowledgeUnit,
    RelationshipType,
)


def test_semantic_chunk_aggregation_and_prereqs() -> None:
    """Verify semantic chunk groupings, evidence mappings, and prerequisite collections."""
    pipeline = SemanticChunkBuilderPipeline()
    context = PipelineContext()

    artifact = ArtifactMetadata(
        artifact_id=uuid.uuid4(),
        checksum="hash_doc",
        created_at=datetime.now(timezone.utc),
    )

    c1 = Concept(
        concept_id=uuid.uuid5(uuid.NAMESPACE_DNS, "c1"),
        canonical_name="Concept 1",
        aliases=[],
        subject="DBMS",
        difficulty="easy",
    )
    c2 = Concept(
        concept_id=uuid.uuid5(uuid.NAMESPACE_DNS, "c2"),
        canonical_name="Concept 2",
        aliases=[],
        subject="DBMS",
        difficulty="hard",
    )

    u1 = KnowledgeUnit(
        unit_id=uuid.uuid4(),
        type=KnowledgeType.DEFINITION,
        content="Concept 1 Definition content.",
        occurrence_ids=[],
        evidence_ids=[uuid.uuid4()],
    )

    rel = ConceptRelationship(
        relationship_id=uuid.uuid4(),
        source_concept_id=c1.concept_id,
        target_concept_id=c2.concept_id,
        type=RelationshipType.DEPENDS_ON,
        confidence=1.0,
    )

    m1 = ConceptKnowledgeMapping(
        concept_id=c1.concept_id,
        knowledge_unit_ids=[u1.unit_id],
    )

    stats = GraphStatistics(
        concept_count=2,
        relationship_count=1,
        knowledge_unit_count=1,
        edge_density=0.25,
        connected_components=1,
        cycles_detected=0,
        orphan_concepts=0,
    )

    graph = KnowledgeGraph(
        graph_id=uuid.uuid4(),
        namespace="DBMS",
        concepts={c1.concept_id: c1, c2.concept_id: c2},
        knowledge_units={u1.unit_id: u1},
        relationships={rel.relationship_id: rel},
        mappings={uuid.uuid4(): m1},
        statistics=stats,
        artifact=artifact,
    )

    res = pipeline.execute(graph, context)
    col = res.result

    assert len(col.chunks) == 2

    # Find chunk for c1
    chunk_1 = next(c for c in col.chunks if c.concept_id == c1.concept_id)
    assert len(chunk_1.knowledge_units) == 1
    assert chunk_1.knowledge_units[0].content == "Concept 1 Definition content."
    assert len(chunk_1.evidence_ids) == 1
    assert len(chunk_1.outgoing_relationships) == 1

    # Find chunk for c2 (has c1 as dependency prereq)
    chunk_2 = next(c for c in col.chunks if c.concept_id == c2.concept_id)
    assert c1.concept_id in chunk_2.prerequisites
    assert len(chunk_2.incoming_relationships) == 1

    # Check validation warning because chunk_2 has no mapped units
    assert any("lacks mapped Knowledge Units" in w for w in context.warnings)
