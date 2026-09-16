"""Contract definition for training results."""

class TrainingContract:
    """Defines requirements, preconditions, and invariants for training runs.

    Invariants:
        1. A training run must output a unique run_id.
        2. Status must be one of: 'completed', 'failed'.
        3. A completed training result must expose a valid adapter file path.
        4. Losses (training and validation) must be positive floats.
    """
    ALLOWED_STATUSES = {"completed", "failed"}
