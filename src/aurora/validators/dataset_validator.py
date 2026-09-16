"""Validator for InstructionDataset models."""

from aurora.contracts.dataset_contract import DatasetContract
from aurora.core.exceptions import InterfaceError
from aurora.models.dataset import InstructionDataset


def validate_dataset(dataset: InstructionDataset) -> None:
    """Validate dataset complies with DatasetContract rules."""
    if not dataset.name.strip():
        raise InterfaceError("Dataset name cannot be empty.")
    if dataset.split not in DatasetContract.ALLOWED_SPLITS:
        raise InterfaceError(
            f"Dataset split '{dataset.split}' is invalid. "
            f"Must be one of {DatasetContract.ALLOWED_SPLITS}"
        )
    if not dataset.pairs:
        raise InterfaceError("Dataset must contain at least one QA pair.")

    for i, pair in enumerate(dataset.pairs):
        if not pair.instruction.strip():
            raise InterfaceError(f"QA pair at index {i} has empty instruction.")
        if not pair.response.strip():
            raise InterfaceError(f"QA pair at index {i} has empty response.")
        if not pair.reference_concept.strip():
            raise InterfaceError(f"QA pair at index {i} has empty reference concept.")
