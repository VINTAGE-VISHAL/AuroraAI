"""Validator for Curriculum models."""

from aurora.core.exceptions import InterfaceError
from aurora.models.curriculum import Curriculum
from aurora.validators.concept_validator import validate_concept


def validate_curriculum(curriculum: Curriculum) -> None:
    """Validate curriculum complies with CurriculumContract rules."""
    if not curriculum.domain.strip():
        raise InterfaceError("Curriculum domain title cannot be empty.")

    concept_names = {c.name for c in curriculum.concepts}
    for concept in curriculum.concepts:
        validate_concept(concept)
        # Check prerequisites reference valid concepts
        for prereq in concept.prerequisites:
            if prereq not in concept_names:
                raise InterfaceError(
                    f"Concept '{concept.name}' references non-existent prerequisite: '{prereq}'"
                )
