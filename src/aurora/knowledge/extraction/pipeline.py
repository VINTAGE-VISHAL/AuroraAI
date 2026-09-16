"""Pipeline orchestrator for rule-based Concept Extraction from StructuredDocuments."""

import hashlib
import re
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional, Set

from aurora.core.pipeline import BasePipeline, IPipelineStep, PipelineContext, PipelineResult
from aurora.knowledge.extraction.interfaces import ICandidateDiscoveryStrategy
from aurora.knowledge.extraction.strategies import (
    BoldPatternMatcher,
    DefinitionPatternMatcher,
    HeadingPatternMatcher,
)
from aurora.models import ArtifactMetadata, Concept, ExtractedConceptCollection, StructuredDocument


class CandidateDiscoveryStep(IPipelineStep[StructuredDocument, List[str]]):
    """Executes registered strategies to aggregate raw concept string candidates."""

    def __init__(self, strategies: Optional[List[ICandidateDiscoveryStrategy]] = None) -> None:
        self.strategies = strategies or [
            HeadingPatternMatcher(),
            BoldPatternMatcher(),
            DefinitionPatternMatcher(),
        ]

    def process(self, input_data: StructuredDocument, context: PipelineContext) -> List[str]:
        candidates: List[str] = []
        for strategy in self.strategies:
            candidates.extend(strategy.discover(input_data))
        return candidates


class CandidateNormalizationStep(IPipelineStep[List[str], List[str]]):
    """Normalizes candidates spacing, casing, and resolves standard acronym mappings."""

    ACRONYM_MAP = {
        "dbms": "Database Management System",
        "bcnf": "Boyce-Codd Normal Form",
        "3nf": "Third Normal Form",
        "2nf": "Second Normal Form",
        "1nf": "First Normal Form",
        "acid": "Atomicity Consistency Isolation Durability",
    }

    def process(self, input_data: List[str], context: PipelineContext) -> List[str]:
        normalized: List[str] = []
        for val in input_data:
            # Clean repeated spaces
            cleaned = re.sub(r"\s+", " ", val).strip()
            if not cleaned:
                continue

            lower_val = cleaned.lower()
            # Map acronyms to expanded canonical form
            if lower_val in self.ACRONYM_MAP:
                normalized.append(self.ACRONYM_MAP[lower_val])
            else:
                # Standardize title case for canonical concepts
                normalized.append(cleaned.title())
        return normalized


class CandidateValidationStep(IPipelineStep[List[str], List[str]]):
    """Filters out stop words, digits, single letters, and duplicate entries."""

    STOP_WORDS = {
        "the", "and", "a", "of", "in", "to", "for", "with", "on", "at",
        "by", "an", "is", "this", "that"
    }

    def process(self, input_data: List[str], context: PipelineContext) -> List[str]:
        validated: List[str] = []
        seen: Set[str] = set()

        for val in input_data:
            cleaned = val.strip()
            if not cleaned:
                continue

            # Length bounds check
            words = cleaned.split()
            if len(words) < 2 and cleaned.lower() in self.STOP_WORDS:
                continue
            if len(cleaned) <= 2:
                continue
            if len(words) > 5:
                continue

            # Digits only check
            if cleaned.isdigit():
                continue

            # Deduplication
            lower_val = cleaned.lower()
            if lower_val not in seen:
                seen.add(lower_val)
                validated.append(cleaned)

        return validated


class ConceptAssemblyStep(IPipelineStep[List[str], List[Concept]]):
    """Compiles normalized candidates into strongly typed Concept domain models."""

    ACRONYM_REVERSE = {
        "Database Management System": ["DBMS"],
        "Boyce-Codd Normal Form": ["BCNF"],
        "Third Normal Form": ["3NF"],
        "Second Normal Form": ["2NF"],
        "First Normal Form": ["1NF"],
        "Atomicity Consistency Isolation Durability": ["ACID"],
    }

    def process(self, input_data: List[str], context: PipelineContext) -> List[Concept]:
        concepts: List[Concept] = []
        for val in input_data:
            # Generate deterministic UUID based on lowercase canonical name
            concept_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, val.lower())

            # Map reverse acronyms as aliases if exists
            aliases = self.ACRONYM_REVERSE.get(val, [])

            concepts.append(
                Concept(
                    concept_id=concept_uuid,
                    canonical_name=val,
                    aliases=aliases,
                    subject="Computer Science",
                    difficulty="intermediate",
                    metadata={"source": "RuleBasedConceptExtractor"},
                )
            )
        return concepts


class ConceptExtractorPipeline(BasePipeline[StructuredDocument, ExtractedConceptCollection]):
    """Orchestrates candidate discovery, normalization, validation, and concept assembly."""

    def __init__(self, steps: Optional[List[IPipelineStep[Any, Any]]] = None) -> None:
        if steps is None:
            default_steps: List[IPipelineStep[Any, Any]] = [
                CandidateDiscoveryStep(),
                CandidateNormalizationStep(),
                CandidateValidationStep(),
                ConceptAssemblyStep(),
            ]
            super().__init__(default_steps)
        else:
            super().__init__(steps)

    def execute(
        self, input_data: StructuredDocument, context: PipelineContext
    ) -> PipelineResult[ExtractedConceptCollection]:
        """Runs the pipeline execution, tracking candidates metrics and compilation."""
        # Step 1: Discover candidates
        discovery_step = self.steps[0]
        raw_candidates = discovery_step.process(input_data, context)
        context.metrics["candidates_discovered"] = len(raw_candidates)

        # Step 2: Normalize candidates
        normalization_step = self.steps[1]
        normalized_candidates = normalization_step.process(raw_candidates, context)

        # Step 3: Validate candidates
        validation_step = self.steps[2]
        validated_candidates = validation_step.process(normalized_candidates, context)
        context.metrics["concepts_accepted"] = len(validated_candidates)
        context.metrics["duplicates_removed"] = (
            len(normalized_candidates) - len(validated_candidates)
        )

        # Step 4: Assemble concepts
        assembly_step = self.steps[3]
        concepts = assembly_step.process(validated_candidates, context)

        # Build stable ExtractedConceptCollection
        collection_uuid = uuid.uuid4()
        concepts_signature = "".join(str(c.concept_id) for c in concepts)
        checksum = hashlib.sha256(concepts_signature.encode("utf-8")).hexdigest()

        artifact = ArtifactMetadata(
            artifact_id=uuid.uuid4(),
            parent_artifact_ids=[input_data.artifact.artifact_id],
            derived_from=[input_data.artifact.artifact_id],
            checksum=checksum,
            created_at=datetime.now(timezone.utc),
            schema_version="1.0.0",
        )

        collection = ExtractedConceptCollection(
            collection_id=collection_uuid,
            source_document_id=input_data.doc_id,
            concepts=concepts,
            taxonomy_version="1.0.0",
            pipeline_version="1.0.0",
            artifact=artifact,
        )

        return PipelineResult(
            result=collection,
            metrics=context.metrics,
            warnings=context.warnings,
            diagnostics=context.diagnostics,
        )
