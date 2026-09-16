"""Pipeline orchestrator for Concept Taxonomy construction and execution."""

import hashlib
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from aurora.core.exceptions import TaxonomyError
from aurora.core.pipeline import BasePipeline, PipelineContext, PipelineResult
from aurora.knowledge.taxonomy.interfaces import ITaxonomyStep
from aurora.knowledge.taxonomy.validators import TaxonomyValidationStep
from aurora.models import ArtifactMetadata, Concept, ConceptTaxonomy


class TaxonomyPipeline(BasePipeline[List[Concept], ConceptTaxonomy]):
    """Orchestrates sequential validation and building of the Concept Taxonomy."""

    def __init__(self, name: str, steps: Optional[List[ITaxonomyStep]] = None) -> None:
        self.name = name
        if steps is None:
            # Default sequence: Validation step
            default_steps: List[ITaxonomyStep] = [
                TaxonomyValidationStep(),
            ]
            super().__init__(default_steps)  # type: ignore
        else:
            super().__init__(steps)  # type: ignore

    def execute(
        self, input_data: List[Concept], context: PipelineContext
    ) -> PipelineResult[ConceptTaxonomy]:
        """Validates input concepts, builds taxonomy, and returns PipelineResult."""
        current_concepts = input_data

        try:
            for step in self.steps:
                current_concepts = step.process(current_concepts, context)
        except Exception as e:
            if not isinstance(e, TaxonomyError):
                raise TaxonomyError(f"Taxonomy pipeline execution failed: {e}") from e
            raise

        # Generate deterministic taxonomy ID using namespace uuid5
        taxonomy_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, self.name)

        # Generate deterministic checksum for lineage tracking
        concepts_signature = "".join(str(c.concept_id) for c in current_concepts)
        checksum = hashlib.sha256(concepts_signature.encode("utf-8")).hexdigest()

        artifact = ArtifactMetadata(
            artifact_id=uuid.uuid4(),
            checksum=checksum,
            created_at=datetime.now(timezone.utc),
            schema_version="1.0.0",
        )

        result_taxonomy = ConceptTaxonomy(
            taxonomy_id=taxonomy_uuid,
            name=self.name,
            concepts=current_concepts,
            artifact=artifact,
        )

        return PipelineResult(
            result=result_taxonomy,
            metrics=context.metrics,
            warnings=context.warnings,
            diagnostics=context.diagnostics,
        )
