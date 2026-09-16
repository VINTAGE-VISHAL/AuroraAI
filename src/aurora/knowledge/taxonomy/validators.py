"""Validator steps validating concept uniqueness and constraint rules."""

from typing import List, Set

from aurora.core.exceptions import DuplicateConceptError, EmptyConceptError, InvalidTaxonomyError
from aurora.core.pipeline import PipelineContext
from aurora.knowledge.taxonomy.interfaces import ITaxonomyStep
from aurora.models import Concept


class TaxonomyValidationStep(ITaxonomyStep):
    """Enforces concept uniqueness, non-emptiness, and ontology integrity rules."""

    def _validate_integrity(self, concept: Concept) -> None:
        """Verify non-emptiness, subject existence, and difficulty range."""
        canonical = concept.canonical_name.strip()
        if not canonical:
            raise EmptyConceptError("Concept canonical name cannot be empty.")

        if not concept.subject.strip():
            raise InvalidTaxonomyError(
                f"Concept '{canonical}' must have a valid subject."
            )

        valid_difficulties = {"beginner", "intermediate", "advanced"}
        if concept.difficulty.lower() not in valid_difficulties:
            raise InvalidTaxonomyError(
                f"Concept '{canonical}' has invalid difficulty level: '{concept.difficulty}'"
            )

    def _validate_duplicates(
        self, concept: Concept, seen_names: Set[str], seen_aliases: Set[str]
    ) -> None:
        """Ensure canonical names and aliases do not collide."""
        canonical = concept.canonical_name.strip()
        lower_name = canonical.lower()

        if lower_name in seen_names:
            raise DuplicateConceptError(
                f"Concept name '{canonical}' is registered multiple times."
            )
        if lower_name in seen_aliases:
            raise DuplicateConceptError(
                f"Concept name '{canonical}' conflicts with a registered alias."
            )
        seen_names.add(lower_name)

        for alias in concept.aliases:
            cleaned_alias = alias.strip().lower()
            if not cleaned_alias:
                continue
            if cleaned_alias in seen_names:
                raise DuplicateConceptError(
                    f"Alias '{alias}' on concept '{canonical}' conflicts with "
                    "a registered canonical name."
                )
            if cleaned_alias in seen_aliases:
                raise DuplicateConceptError(
                    f"Alias '{alias}' on concept '{canonical}' is registered multiple times."
                )
            seen_aliases.add(cleaned_alias)

    def process(
        self, input_data: List[Concept], context: PipelineContext
    ) -> List[Concept]:
        seen_names: Set[str] = set()
        seen_aliases: Set[str] = set()

        for concept in input_data:
            self._validate_integrity(concept)
            self._validate_duplicates(concept, seen_names, seen_aliases)

        return input_data

