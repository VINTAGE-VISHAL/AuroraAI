"""Validators enforcing structural completeness and educational groundedness."""

from typing import List

from aurora.models import DatasetCollection


class StructuralValidator:
    """Enforces prompt, output, and ID completeness validations."""

    def validate(self, collection: DatasetCollection, warnings: List[str]) -> bool:
        """Returns True if structural parameters pass constraints, False otherwise."""
        is_valid = True
        for ex in collection.examples:
            if not ex.input.strip():
                warnings.append(f"Example '{ex.example_id}' contains empty input prompt.")
                is_valid = False
            if not ex.output.strip():
                warnings.append(f"Example '{ex.example_id}' contains empty output response.")
                is_valid = False
            if not ex.format_tag.strip():
                warnings.append(f"Example '{ex.example_id}' lacks format tag annotation.")
                is_valid = False
        return is_valid


class EducationalValidator:
    """Validates trace links back to the source Knowledge Graph and Semantic Chunks."""

    def validate(self, collection: DatasetCollection, warnings: List[str]) -> bool:
        """Returns True if all examples are trace-grounded, False otherwise."""
        is_valid = True
        for ex in collection.examples:
            trace = ex.traceability
            if not trace.knowledge_unit_ids:
                warnings.append(
                    f"Example '{ex.example_id}' violates groundedness: "
                    "no mapped Knowledge Unit IDs."
                )
                is_valid = False
            if not trace.concept_ids:
                warnings.append(
                    f"Example '{ex.example_id}' violates groundedness: "
                    "no mapped Concept IDs."
                )
                is_valid = False
        return is_valid
