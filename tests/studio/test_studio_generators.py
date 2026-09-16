"""Unit tests for Dataset Studio generator plugins."""

import uuid
from datetime import datetime, timezone

from aurora.core.pipeline import PipelineContext
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
    SemanticChunk,
    SemanticChunkCollection,
)
from aurora.studio.context import DatasetGenerationContext
from aurora.studio.generators.flashcard import FlashcardGenerator
from aurora.studio.generators.mcq import MCQGenerator
from aurora.studio.generators.tutor import TutorGenerator
from aurora.studio.pipeline import DatasetStudioPipeline
from aurora.studio.templates import PromptTemplateRegistry


def test_tutor_mcq_flashcard_generators() -> None:
    """Verify tutor, MCQ, and flashcard generation templates vs rules logic."""
    artifact = ArtifactMetadata(
        artifact_id=uuid.uuid4(),
        checksum="hash_doc",
        created_at=datetime.now(timezone.utc),
    )

    c1 = Concept(
        concept_id=uuid.uuid5(uuid.NAMESPACE_DNS, "c1"),
        canonical_name="Concept 1",
        aliases=[],
        subject="CS",
        difficulty="easy",
    )
    c2 = Concept(
        concept_id=uuid.uuid5(uuid.NAMESPACE_DNS, "c2"),
        canonical_name="Concept 2",
        aliases=[],
        subject="CS",
        difficulty="intermediate",
    )

    u1 = KnowledgeUnit(
        unit_id=uuid.uuid4(),
        type=KnowledgeType.DEFINITION,
        content="Unit 1 definition content.",
        occurrence_ids=[],
        evidence_ids=[],
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

    chunk_1 = SemanticChunk(
        chunk_id=uuid.uuid4(),
        concept_id=c1.concept_id,
        concept_name=c1.canonical_name,
        knowledge_units=[u1],
        incoming_relationships=[],
        outgoing_relationships=[rel],
        prerequisites=[],
        evidence_ids=[],
        metadata={"difficulty": "easy"},
    )

    chunk_col = SemanticChunkCollection(
        collection_id=uuid.uuid4(),
        chunks=[chunk_1],
        artifact=artifact,
    )

    registry = PromptTemplateRegistry()

    context = DatasetGenerationContext(
        graph=graph,
        chunks=chunk_col,
        template_registry={
            "tutor": registry.get_template("tutor"),
            "mcq": registry.get_template("mcq"),
            "flashcard": registry.get_template("flashcard"),
        },
    )

    pipeline = DatasetStudioPipeline(
        generators=[TutorGenerator(), MCQGenerator(), FlashcardGenerator()]
    )
    p_context = PipelineContext()

    res = pipeline.execute(context, p_context)
    collection = res.result

    assert len(collection.examples) == 3

    tutor_ex = next(ex for ex in collection.examples if ex.format_tag == "tutor")
    assert "Concept 1" in tutor_ex.input
    assert tutor_ex.traceability.concept_ids == [c1.concept_id]

    mcq_ex = next(ex for ex in collection.examples if ex.format_tag == "mcq")
    assert "Question:" in mcq_ex.output
