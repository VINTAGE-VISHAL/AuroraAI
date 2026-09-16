"""Contract definition for educational datasets."""

class DatasetContract:
    """Defines requirements, preconditions, and invariants for datasets.

    Invariants:
        1. A dataset must possess a non-empty name.
        2. A dataset must consist of a collection of QA pairs.
        3. Every QA pair must contain a non-empty instruction,
           non-empty response, and a referenced concept.
        4. Split type must be one of: 'train', 'validation', 'test'.
    """
    ALLOWED_SPLITS = {"train", "validation", "test"}
