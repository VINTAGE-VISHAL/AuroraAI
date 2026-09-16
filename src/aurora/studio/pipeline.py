"""Orchestrator pipeline executing generator plugins, validations, and statistics reporting."""

from typing import Dict, List
from uuid import uuid4

from aurora.core.exceptions import AuroraError
from aurora.core.pipeline import PipelineContext, PipelineResult
from aurora.models import DatasetCollection, DatasetExample, DatasetStatistics
from aurora.studio.context import DatasetGenerationContext
from aurora.studio.interfaces import IDatasetGenerator
from aurora.studio.validators import EducationalValidator, StructuralValidator


class DatasetStudioPipeline:
    """Orchestrates generation of datasets from semantic chunks and graph topologies."""

    def __init__(self, generators: List[IDatasetGenerator]) -> None:
        self.generators = generators
        self.structural_validator = StructuralValidator()
        self.educational_validator = EducationalValidator()

    def execute(
        self, context: DatasetGenerationContext, pipeline_context: PipelineContext
    ) -> PipelineResult[DatasetCollection]:
        """Runs the generation plugin lifecycle, validates grounding, and compiles output."""
        all_examples: List[DatasetExample] = []

        # 1. Run all plugin generators
        for generator in self.generators:
            try:
                col = generator.generate(context)
                all_examples.extend(col.examples)
            except Exception as e:
                raise AuroraError(
                    f"Dataset generation failed in generator '{generator.descriptor.name}': {e}"
                ) from e

        combined_collection = DatasetCollection(
            collection_id=uuid4(),
            examples=all_examples,
        )

        # 2. Validation Stage
        warnings: List[str] = []
        is_struct_valid = self.structural_validator.validate(
            combined_collection, warnings
        )
        is_edu_valid = self.educational_validator.validate(
            combined_collection, warnings
        )

        if not is_struct_valid or not is_edu_valid:
            pipeline_context.warnings.extend(warnings)

        # 3. Calculate statistics
        total = len(all_examples)
        formats: Dict[str, int] = {}
        diffs: Dict[str, int] = {}
        for ex in all_examples:
            formats[ex.format_tag] = formats.get(ex.format_tag, 0) + 1
            diff = ex.metadata.get("difficulty", "unknown")
            diffs[diff] = diffs.get(diff, 0) + 1

        # Coverage checks against graph
        graph_concept_ids = set(context.graph.concepts.keys())
        graph_unit_ids = set(context.graph.knowledge_units.keys())

        represented_concepts = set()
        represented_units = set()
        for ex in all_examples:
            represented_concepts.update(ex.traceability.concept_ids)
            represented_units.update(ex.traceability.knowledge_unit_ids)

        concept_cov = (
            len(represented_concepts & graph_concept_ids) / len(graph_concept_ids)
            if graph_concept_ids
            else 0.0
        )
        unit_cov = (
            len(represented_units & graph_unit_ids) / len(graph_unit_ids)
            if graph_unit_ids
            else 0.0
        )

        # Duplicate rate checks
        seen_prompts = set()
        duplicates = 0
        for ex in all_examples:
            if ex.input in seen_prompts:
                duplicates += 1
            seen_prompts.add(ex.input)

        dup_rate = duplicates / total if total > 0 else 0.0
        val_score = 1.0 if (is_struct_valid and is_edu_valid) else 0.5

        stats = DatasetStatistics(
            total_examples=total,
            format_distribution=formats,
            concept_coverage=concept_cov,
            difficulty_distribution=diffs,
            knowledge_unit_coverage=unit_cov,
            duplicate_rate=dup_rate,
            validation_score=val_score,
        )

        pipeline_context.diagnostics["statistics"] = stats
        pipeline_context.diagnostics["warnings_logged"] = warnings

        return PipelineResult(
            result=combined_collection,
            metrics=pipeline_context.metrics,
            warnings=pipeline_context.warnings,
            diagnostics=pipeline_context.diagnostics,
        )
