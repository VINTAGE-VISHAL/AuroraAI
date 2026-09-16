"""Unit tests for the Knowledge Graph Builder Subsystem."""

import uuid
from datetime import datetime, timezone

import pytest

from aurora.core.exceptions import InvalidGraphReferenceError
from aurora.core.pipeline import PipelineContext
from aurora.knowledge.graph.exporters import GraphMLExporter, JsonExporter
from aurora.knowledge.graph.pipeline import KnowledgeGraphBuilderPipeline
from aurora.models import (
    ArtifactMetadata,
    Concept,
    ConceptKnowledgeMapping,
    ConceptRelationship,
    ConceptRelationshipCollection,
    ExtractedConceptCollection,
    FrameworkInfo,
    KnowledgeType,
    KnowledgeUnit,
    KnowledgeUnitCollection,
    PipelineProvenance,
    RelationshipType,
)
from aurora.models.enums import DocumentState


def test_knowledge_graph_assembly_and_metrics() -> None:
    """Verify normal assembly, quality checks, statistics, and cycle checks."""
    pipeline = KnowledgeGraphBuilderPipeline()
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

    c1 = Concept(
        concept_id=uuid.uuid5(uuid.NAMESPACE_DNS, "c1"),
        canonical_name="Concept 1",
        aliases=[],
        subject="Computer Science",
        difficulty="easy",
    )
    c2 = Concept(
        concept_id=uuid.uuid5(uuid.NAMESPACE_DNS, "c2"),
        canonical_name="Concept 2",
        aliases=[],
        subject="Computer Science",
        difficulty="intermediate",
    )
    c3 = Concept(
        concept_id=uuid.uuid5(uuid.NAMESPACE_DNS, "c3"),
        canonical_name="Orphan Concept",
        aliases=[],
        subject="Computer Science",
        difficulty="intermediate",
    )

    concept_col = ExtractedConceptCollection(
        collection_id=uuid.uuid4(),
        source_document_id="doc123",
        concepts=[c1, c2, c3],
        taxonomy_version="1.0.0",
        pipeline_version="1.0.0",
        artifact=artifact,
    )

    u1 = KnowledgeUnit(
        unit_id=uuid.uuid4(),
        type=KnowledgeType.DEFINITION,
        content="Unit 1 definition content.",
        occurrence_ids=[],
        evidence_ids=[],
    )

    unit_col = KnowledgeUnitCollection(
        collection_id=uuid.uuid4(),
        source_document_id="doc123",
        units=[u1],
        mappings=[
            ConceptKnowledgeMapping(
                concept_id=c1.concept_id,
                knowledge_unit_ids=[u1.unit_id],
            )
        ],
        artifact=artifact,
    )

    rel = ConceptRelationship(
        relationship_id=uuid.uuid4(),
        source_concept_id=c1.concept_id,
        target_concept_id=c2.concept_id,
        type=RelationshipType.DEPENDS_ON,
        confidence=1.0,
    )

    rel_col = ConceptRelationshipCollection(
        collection_id=uuid.uuid4(),
        source_document_id="doc123",
        graph_namespace="OS",
        relationships=[rel],
        evidences=[],
        artifact=artifact,
    )

    res = pipeline.execute((concept_col, unit_col, rel_col), context)
    graph = res.result

    # Check structural indices
    assert graph.namespace == "OS"
    assert graph.concepts[c1.concept_id].canonical_name == "Concept 1"
    assert graph.knowledge_units[u1.unit_id].content == "Unit 1 definition content."
    assert len(graph.relationships) == 1

    # Check statistics calculations
    assert graph.statistics.concept_count == 3
    assert graph.statistics.relationship_count == 1
    assert graph.statistics.knowledge_unit_count == 1
    assert graph.statistics.orphan_concepts == 1  # c3 is orphan

    # Export checks
    json_data = JsonExporter().export(graph)
    assert "namespace" in json_data
    assert "OS" in json_data

    graphml_data = GraphMLExporter().export(graph)
    assert "<graphml" in graphml_data
    assert "concept" in graphml_data


def test_knowledge_graph_invalid_references() -> None:
    """Verify that graph builder raises InvalidGraphReferenceError on bad references."""
    pipeline = KnowledgeGraphBuilderPipeline()
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

    c1 = Concept(
        concept_id=uuid.uuid4(),
        canonical_name="Concept 1",
        aliases=[],
        subject="CS",
        difficulty="easy",
    )

    concept_col = ExtractedConceptCollection(
        collection_id=uuid.uuid4(),
        source_document_id="doc123",
        concepts=[c1],
        taxonomy_version="1.0.0",
        pipeline_version="1.0.0",
        artifact=artifact,
    )

    # Reference invalid concept ID in mapping
    unit_col = KnowledgeUnitCollection(
        collection_id=uuid.uuid4(),
        source_document_id="doc123",
        units=[],
        mappings=[
            ConceptKnowledgeMapping(
                concept_id=uuid.uuid4(),  # Bad ID
                knowledge_unit_ids=[],
            )
        ],
        artifact=artifact,
    )

    rel_col = ConceptRelationshipCollection(
        collection_id=uuid.uuid4(),
        source_document_id="doc123",
        graph_namespace="OS",
        relationships=[],
        evidences=[],
        artifact=artifact,
    )

    with pytest.raises(InvalidGraphReferenceError):
        pipeline.execute((concept_col, unit_col, rel_col), context)
