"""DatasetLoader component for Phase D."""

from typing import Any, Tuple
from datasets import Dataset

from aurora.core.exceptions import InterfaceError
from aurora.interfaces.training import IDatasetLoader
from aurora.models import TrainingInput, PreparedDataset
from aurora.models.training_corpus import SerializedSample


class DatasetLoader(IDatasetLoader):
    """Loads and validates JSONL datasets for QLoRA training using strong domain model validation."""

    def load(self, training_input: TrainingInput) -> Tuple[Dataset, PreparedDataset]:
        """Loads and validates a datasets.Dataset from the TrainingInput.

        Returns:
            A tuple of (hf_dataset, PreparedDataset metadata).
        """
        raw_samples = self._load_jsonl(training_input.dataset_path)
        dataset = self._create_dataset(raw_samples)
        metadata = self._prepare_dataset(training_input)
        return dataset, metadata

    def _load_jsonl(self, dataset_path: str) -> list[SerializedSample]:
        """Reads JSONL lines from the target dataset path and validates them into SerializedSamples."""
        samples: list[SerializedSample] = []
        try:
            with open(dataset_path, "r", encoding="utf-8") as f:
                for line_idx, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    try:
                        # Pydantic model_validate_json enforces type validation on sample_id, sequence_number, and payload
                        sample = SerializedSample.model_validate_json(line)
                        samples.append(sample)
                    except Exception as e:
                        raise InterfaceError(
                            f"Validation failed: JSON on line {line_idx} of '{dataset_path}' violates SerializedSample schema: {e}"
                        )
        except Exception as e:
            if isinstance(e, InterfaceError):
                raise
            raise InterfaceError(f"Failed to read dataset file '{dataset_path}': {e}")
        return samples

    def _create_dataset(self, samples: list[SerializedSample]) -> Dataset:
        """Builds a Hugging Face Dataset in a deterministic sequence."""
        if not samples:
            raise InterfaceError("Dataset is empty. No training samples found.")

        # Extract fields to ensure deterministic order and structure
        data_dict = {
            "sample_id": [s.sample_id for s in samples],
            "sequence_number": [s.sequence_number for s in samples],
            # SerializedSample.payload is a pydantic model subclass of SerializedPayload
            "payload": [s.payload.model_dump() for s in samples],
        }
        return Dataset.from_dict(data_dict)

    def _prepare_dataset(self, training_input: TrainingInput) -> PreparedDataset:
        """Wraps configuration metrics in the domain-level PreparedDataset metadata model."""
        return PreparedDataset(
            sample_count=training_input.sample_count,
            checksum=training_input.checksum,
            dataset_path=training_input.dataset_path,
        )
