from abc import ABC, abstractmethod
from typing import Any, Tuple
from aurora.interfaces.base import IPipelineComponent
from aurora.models import ExportResult, TrainingConfig, TrainingInput, PreparedDataset, RawTrainingOutput, CheckpointInfo, EvaluationResult
from aurora.models.training import TrainingResult


class ITrainingInputAdapter(ABC):
    """Interface for adapting Phase C export results and configuration to QLoRA trainer input."""

    @abstractmethod
    def adapt(
        self,
        export_result: ExportResult,
        config: TrainingConfig,
    ) -> TrainingInput:
        """Adapts and validates Phase C export output into training input structures.

        Raises:
            InterfaceError: If validation checks fail or dataset path is unreachable.
        """
        pass


class IDatasetLoader(ABC):
    """Interface for loading and validating datasets for QLoRA training."""

    @abstractmethod
    def load(
        self,
        training_input: TrainingInput,
    ) -> Tuple[Any, PreparedDataset]:
        """Loads and validates a datasets.Dataset from the TrainingInput.

        Returns:
            A tuple containing:
                - hf_dataset: The Hugging Face datasets.Dataset object.
                - PreparedDataset: Clean metadata domain model.

        Raises:
            InterfaceError: If validation checks fail.
        """
        pass


class ITokenizerService(ABC):
    """Interface for tokenizing prepared training datasets for downstream model fine-tuning."""

    @abstractmethod
    def tokenize(
        self,
        hf_dataset: Any,
        tokenizer: Any,
        config: TrainingConfig,
    ) -> Any:  # Returns a tokenized Hugging Face datasets.Dataset
        """Converts and tokenizes messages/text into input_ids, attention_mask, and labels."""
        pass


class IModelPreparer(ABC):
    """Interface for loading base models and injecting LoRA adapters for QLoRA fine-tuning."""

    @abstractmethod
    def prepare(
        self,
        config: TrainingConfig,
    ) -> Tuple[Any, Any]:  # Returns a tuple of (ready_to_train_model, tokenizer)
        """Loads base model, tokenizer, configures quantization, and injects PEFT LoRA adapters.

        Raises:
            InterfaceError: If model loading, quantization, or adapter injection fails.
        """
        pass


class ITrainer(IPipelineComponent[TrainingInput, RawTrainingOutput]):
    """Contract for LoRA-based and fine-tuning model adaptions."""

    @abstractmethod
    def run(self, input_data: TrainingInput) -> RawTrainingOutput:
        """Trains/tunes model weights from the engineered dataset."""
        pass


class ICheckpointManager(ABC):
    """Interface for managing training checkpoints (scanning, validation, cleaning)."""

    @abstractmethod
    def scan(self, output_dir: str) -> list[CheckpointInfo]:
        """Scans the output directory for valid Hugging Face adapter checkpoints.

        Returns:
            A sorted list of valid checkpoints.
        """
        pass

    @abstractmethod
    def prune(self, checkpoints: list[CheckpointInfo], keep_last: int) -> None:
        """Removes older checkpoints to manage storage footprint, keeping the last N checkpoints."""
        pass


class IEvaluator(ABC):
    """Interface for evaluating trained models and computing validation metrics."""

    @abstractmethod
    def evaluate(
        self,
        raw_output: RawTrainingOutput,
        eval_dataset: Any,
        config: TrainingConfig,
    ) -> EvaluationResult:
        """Evaluates model performance and calculates validation metrics."""
        pass


class IAdapterPackager(ABC):
    """Interface for packaging trained model weights, tokenizers, and metadata for deployment."""

    @abstractmethod
    def package(
        self,
        raw_output: RawTrainingOutput,
        evaluation: EvaluationResult,
        config: TrainingConfig,
    ) -> TrainingResult:
        """Saves weights, tokenizers, and metadata to output directories, returning the final TrainingResult."""
        pass
