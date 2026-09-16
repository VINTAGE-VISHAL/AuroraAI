"""Validator for TrainingResult models."""

from aurora.core.exceptions import InterfaceError
from aurora.models.training import TrainingResult


def validate_training_result(result: TrainingResult) -> None:
    """Validate training result complies with TrainingContract rules."""
    if result.success and not result.adapter_path.strip():
        raise InterfaceError("Successful training result must specify an adapter path.")
    if result.final_loss < 0:
        raise InterfaceError("Loss values cannot be negative.")
