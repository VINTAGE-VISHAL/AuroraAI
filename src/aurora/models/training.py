"""Domain models defining QLoRA model training structures."""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, field_validator, model_validator


from aurora.models.training_corpus import ExportFormat


class ComputeDType(str, Enum):
    """Supported computation precision data types for BitsAndBytes config."""
    FLOAT16 = "float16"
    BFLOAT16 = "bfloat16"
    FLOAT32 = "float32"


class TrainingConfig(BaseModel):
    """Configuration parameters for a QLoRA adapter training session."""
    model_config = ConfigDict(frozen=True)

    model_name: str
    tokenizer_name: str
    dataset_path: str
    output_dir: str

    epochs: int
    batch_size: int
    gradient_accumulation_steps: int

    learning_rate: float
    warmup_ratio: float
    weight_decay: float

    max_seq_length: int
    seed: int

    lora_r: int
    lora_alpha: int
    lora_dropout: float
    target_modules: List[str]

    load_in_4bit: bool
    bnb_compute_dtype: ComputeDType
    quant_type: str = "nf4"

    bf16: bool
    fp16: bool

    gradient_checkpointing: bool
    device_map: str = "auto"
    trust_remote_code: bool = False

    save_steps: int
    logging_steps: int
    eval_steps: int
    eval_threshold: float = 1.0
    max_steps: int = -1

    resume_checkpoint: Optional[str] = None

    @field_validator("model_name", "tokenizer_name", "dataset_path", "output_dir", "quant_type", "device_map")
    @classmethod
    def path_fields_must_not_be_empty(cls, v: str) -> str:
        """Ensures that the configurations and path references are not empty strings."""
        if not v or not v.strip():
            raise ValueError("Path/identity field cannot be empty or whitespace-only.")
        return v

    @field_validator("epochs", "batch_size", "gradient_accumulation_steps", "max_seq_length", "lora_r", "lora_alpha")
    @classmethod
    def must_be_positive_int(cls, v: int) -> int:
        """Ensures that positive integers are greater than 0."""
        if v <= 0:
            raise ValueError("Value must be positive.")
        return v

    @field_validator("learning_rate", "weight_decay")
    @classmethod
    def must_be_non_negative_float(cls, v: float) -> float:
        """Ensures floats are positive/non-negative."""
        if v < 0.0:
            raise ValueError("Value must be non-negative.")
        return v

    @field_validator("lora_dropout", "warmup_ratio")
    @classmethod
    def ratio_must_be_valid(cls, v: float) -> float:
        """Ensures probabilities and ratios are within [0, 1]."""
        if not (0.0 <= v <= 1.0):
            raise ValueError("Ratio must be between 0.0 and 1.0.")
        return v

    @field_validator("target_modules")
    @classmethod
    def target_modules_must_not_be_empty(cls, v: List[str]) -> List[str]:
        """Ensures lora target modules are provided and contain no blank entries."""
        if not v:
            raise ValueError("target_modules must contain at least one module name.")
        for module in v:
            if not module or not module.strip():
                raise ValueError("target_modules cannot contain empty or whitespace-only strings.")
        return v

    @model_validator(mode="after")
    def validate_precision_modes(self) -> "TrainingConfig":
        """Ensures exactly one mixed-precision mode (bf16 or fp16) is enabled."""
        if self.bf16 == self.fp16:
            raise ValueError("Exactly one of bf16 or fp16 training precision modes must be True.")
        return self


class TrainingState(BaseModel):
    """Runtime stats tracked during an active training loop."""
    model_config = ConfigDict(frozen=True)

    current_epoch: int
    global_step: int
    completed_steps: int
    train_loss: float
    best_loss: float
    learning_rate: float
    elapsed_time: timedelta
    estimated_remaining_time: Optional[timedelta] = None

    @field_validator("current_epoch", "global_step", "completed_steps")
    @classmethod
    def must_be_non_negative_int(cls, v: int) -> int:
        """Ensures integer metrics are non-negative."""
        if v < 0:
            raise ValueError("Value must be non-negative.")
        return v

    @field_validator("train_loss", "best_loss", "learning_rate")
    @classmethod
    def must_be_non_negative_float(cls, v: float) -> float:
        """Ensures float metrics are non-negative."""
        if v < 0.0:
            raise ValueError("Value must be non-negative.")
        return v


class CheckpointInfo(BaseModel):
    """Metadata representing a saved model checkpoint directory."""
    model_config = ConfigDict(frozen=True)

    checkpoint_name: str
    path: str
    epoch: int
    global_step: int
    loss: float
    timestamp: datetime

    @field_validator("checkpoint_name", "path")
    @classmethod
    def path_fields_must_not_be_empty(cls, v: str) -> str:
        """Ensures identifier fields are populated."""
        if not v or not v.strip():
            raise ValueError("Checkpoint metadata strings cannot be empty.")
        return v

    @field_validator("epoch", "global_step")
    @classmethod
    def must_be_non_negative_int(cls, v: int) -> int:
        """Ensures epoch/step values are non-negative."""
        if v < 0:
            raise ValueError("Value must be non-negative.")
        return v

    @field_validator("loss")
    @classmethod
    def must_be_non_negative_float(cls, v: float) -> float:
        """Ensures loss value is non-negative."""
        if v < 0.0:
            raise ValueError("Value must be non-negative.")
        return v


class EvaluationResult(BaseModel):
    """Report summarizing model accuracy and validation metric outcomes."""
    model_config = ConfigDict(frozen=True)

    loss: float
    perplexity: float
    evaluation_time: timedelta
    passed: bool
    threshold: float = 1.0

    @field_validator("loss", "perplexity")
    @classmethod
    def must_be_non_negative_float(cls, v: float) -> float:
        """Ensures metric results are non-negative."""
        if v < 0.0:
            raise ValueError("Value must be non-negative.")
        return v


class TrainingResult(BaseModel):
    """Immutable outcome report summarizing a completed QLoRA training run."""
    model_config = ConfigDict(frozen=True)

    success: bool
    config: TrainingConfig
    adapter_path: str
    tokenizer_path: str
    checkpoints: List[CheckpointInfo]
    evaluation: EvaluationResult
    training_time: timedelta
    final_loss: float

    @field_validator("final_loss")
    @classmethod
    def must_be_non_negative_float(cls, v: float) -> float:
        """Ensures final training loss is non-negative."""
        if v < 0.0:
            raise ValueError("Value must be non-negative.")
        return v


class TrainingInput(BaseModel):
    """Clean type-safe interface boundary input model for QLoRA Trainer."""
    model_config = ConfigDict(frozen=True)

    dataset_path: str
    config: TrainingConfig
    sample_count: int
    checksum: str
    export_format: ExportFormat


class PreparedDataset(BaseModel):
    """Immutable wrapper around loaded dataset representing validated sample configurations."""
    model_config = ConfigDict(frozen=True)

    sample_count: int
    checksum: str
    dataset_path: str


class RawTrainingOutput(BaseModel):
    """Raw outputs and metrics from model fine-tuning step."""
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    model: Any
    tokenizer: Any
    metrics: dict[str, Any]
    final_loss: float
    training_time: timedelta


