"""Contract definition for concepts."""

class ConceptContract:
    """Defines requirements, preconditions, and invariants for learning concepts.

    Invariants:
        1. A concept must contain a non-empty name and description.
        2. Difficulty value must be one of: 'beginner', 'intermediate', 'advanced'.
        3. A concept must reference at least one source document chunk (reference_chunk_ids).
    """
    ALLOWED_DIFFICULTIES = {"beginner", "intermediate", "advanced"}
