"""Validator for learning Concept models."""

from aurora.contracts.concept_contract import ConceptContract
from aurora.core.exceptions import InterfaceError
from aurora.models.concept import Concept


def validate_concept(concept: Concept) -> None:
    """Validate concept complies with ConceptContract rules."""
    if not concept.name.strip():
        raise InterfaceError("Concept name cannot be empty.")
    if not concept.description.strip():
        raise InterfaceError("Concept description cannot be empty.")
    if concept.difficulty not in ConceptContract.ALLOWED_DIFFICULTIES:
        raise InterfaceError(
            f"Concept difficulty '{concept.difficulty}' is invalid. "
            f"Must be one of {ConceptContract.ALLOWED_DIFFICULTIES}"
        )
    if not concept.reference_chunk_ids:
        raise InterfaceError("Concept must reference at least one chunk ID.")
