"""Unit tests for the Concept Taxonomy Subsystem."""

import uuid

import pytest

from aurora.core.exceptions import DuplicateConceptError, EmptyConceptError, InvalidTaxonomyError
from aurora.core.pipeline import PipelineContext
from aurora.knowledge.taxonomy.pipeline import TaxonomyPipeline
from aurora.models import Concept


def test_taxonomy_valid_pipeline_execution() -> None:
    """Verify that a valid list of concepts builds a correct ConceptTaxonomy."""
    pipeline = TaxonomyPipeline(name="DBMS Taxonomy")
    context = PipelineContext()

    concepts = [
        Concept(
            concept_id=uuid.uuid4(),
            canonical_name="Normalization",
            aliases=["Normalize", "Database Normalization"],
            subject="Database Systems",
            difficulty="intermediate",
        ),
        Concept(
            concept_id=uuid.uuid4(),
            canonical_name="Transactions",
            aliases=["ACID"],
            subject="Database Systems",
            difficulty="advanced",
        ),
    ]

    res = pipeline.execute(concepts, context)
    taxonomy = res.result

    assert taxonomy.name == "DBMS Taxonomy"
    assert len(taxonomy.concepts) == 2
    assert taxonomy.artifact.schema_version == "1.0.0"
    assert taxonomy.artifact.checksum is not None


def test_taxonomy_rejects_empty_name() -> None:
    """Verify EmptyConceptError is raised when concept has empty name."""
    pipeline = TaxonomyPipeline(name="DBMS Taxonomy")
    context = PipelineContext()

    concepts = [
        Concept(
            concept_id=uuid.uuid4(),
            canonical_name="   ",
            aliases=[],
            subject="Database Systems",
            difficulty="intermediate",
        )
    ]

    with pytest.raises(EmptyConceptError):
        pipeline.execute(concepts, context)


def test_taxonomy_rejects_missing_subject() -> None:
    """Verify InvalidTaxonomyError is raised when concept lacks subject."""
    pipeline = TaxonomyPipeline(name="DBMS Taxonomy")
    context = PipelineContext()

    concepts = [
        Concept(
            concept_id=uuid.uuid4(),
            canonical_name="Normalization",
            aliases=[],
            subject="  ",
            difficulty="intermediate",
        )
    ]

    with pytest.raises(InvalidTaxonomyError, match="must have a valid subject"):
        pipeline.execute(concepts, context)


def test_taxonomy_rejects_duplicate_canonical_name() -> None:
    """Verify DuplicateConceptError is raised when canonical names clash (case-insensitive)."""
    pipeline = TaxonomyPipeline(name="DBMS Taxonomy")
    context = PipelineContext()

    concepts = [
        Concept(
            concept_id=uuid.uuid4(),
            canonical_name="Normalization",
            aliases=[],
            subject="Databases",
            difficulty="intermediate",
        ),
        Concept(
            concept_id=uuid.uuid4(),
            canonical_name="normalization",
            aliases=[],
            subject="Databases",
            difficulty="intermediate",
        ),
    ]

    with pytest.raises(DuplicateConceptError, match="registered multiple times"):
        pipeline.execute(concepts, context)


def test_taxonomy_rejects_duplicate_aliases() -> None:
    """Verify DuplicateConceptError is raised when aliases overlap across concepts."""
    pipeline = TaxonomyPipeline(name="DBMS Taxonomy")
    context = PipelineContext()

    concepts = [
        Concept(
            concept_id=uuid.uuid4(),
            canonical_name="Normalization",
            aliases=["Database Normalization"],
            subject="Databases",
            difficulty="intermediate",
        ),
        Concept(
            concept_id=uuid.uuid4(),
            canonical_name="Denormalization",
            aliases=["Database Normalization"],
            subject="Databases",
            difficulty="intermediate",
        ),
    ]

    with pytest.raises(DuplicateConceptError, match="registered multiple times"):
        pipeline.execute(concepts, context)


def test_taxonomy_rejects_alias_canonical_clash() -> None:
    """Verify DuplicateConceptError is raised when alias clashes with a canonical name."""
    pipeline = TaxonomyPipeline(name="DBMS Taxonomy")
    context = PipelineContext()

    concepts = [
        Concept(
            concept_id=uuid.uuid4(),
            canonical_name="Normalization",
            aliases=["Denormalization"],
            subject="Databases",
            difficulty="intermediate",
        ),
        Concept(
            concept_id=uuid.uuid4(),
            canonical_name="Denormalization",
            aliases=[],
            subject="Databases",
            difficulty="intermediate",
        ),
    ]

    with pytest.raises(DuplicateConceptError, match="conflicts"):
        pipeline.execute(concepts, context)


def test_taxonomy_rejects_invalid_difficulty() -> None:
    """Verify InvalidTaxonomyError is raised when difficulty is invalid."""
    pipeline = TaxonomyPipeline(name="DBMS Taxonomy")
    context = PipelineContext()

    concepts = [
        Concept(
            concept_id=uuid.uuid4(),
            canonical_name="Normalization",
            aliases=[],
            subject="Databases",
            difficulty="expert",
        )
    ]

    with pytest.raises(InvalidTaxonomyError, match="invalid difficulty level"):
        pipeline.execute(concepts, context)
