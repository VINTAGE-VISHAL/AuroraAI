"""TrainingInputAdapter implementation for Phase D."""

import os
from aurora.core.exceptions import InterfaceError
from aurora.interfaces.training import ITrainingInputAdapter
from aurora.models import ExportResult, TrainingConfig, TrainingInput


class TrainingInputAdapter(ITrainingInputAdapter):
    """Adapts Phase C ExportResult and TrainingConfig into a validated TrainingInput for Phase D."""

    def adapt(
        self,
        export_result: ExportResult,
        config: TrainingConfig,
    ) -> TrainingInput:
        """Translates and verifies output files and sizes, returning a clean TrainingInput."""
        self._validate_export(export_result)
        self._validate_dataset(export_result.output_path)
        return self._build_training_input(export_result, config)

    def _validate_export(self, export_result: ExportResult) -> None:
        """Validates that Phase C report indicates successful serialization and persistence."""
        if export_result.samples_exported <= 0:
            raise InterfaceError(
                f"Export validation failed: export result reports 0 samples exported."
            )
        if export_result.bytes_written <= 0:
            raise InterfaceError(
                f"Export validation failed: export result reports 0 bytes written."
            )
        if not export_result.checksum or not export_result.checksum.strip():
            raise InterfaceError(
                f"Export validation failed: export result checksum cannot be empty."
            )

    def _validate_dataset(self, dataset_path: str) -> None:
        """Ensures that the target dataset file exists and is accessible/readable."""
        if not os.path.exists(dataset_path):
            raise InterfaceError(
                f"Dataset validation failed: File '{dataset_path}' does not exist on disk."
            )
        if not os.path.isfile(dataset_path):
            raise InterfaceError(
                f"Dataset validation failed: Path '{dataset_path}' is not a valid file."
            )
        if not os.access(dataset_path, os.R_OK):
            raise InterfaceError(
                f"Dataset validation failed: File '{dataset_path}' is not readable (permission denied)."
            )

    def _build_training_input(
        self,
        export_result: ExportResult,
        config: TrainingConfig,
    ) -> TrainingInput:
        """Constructs the strongly typed immutable TrainingInput model."""
        return TrainingInput(
            dataset_path=export_result.output_path,
            config=config,
            sample_count=export_result.samples_exported,
            checksum=export_result.checksum,
            export_format=export_result.format,
        )
