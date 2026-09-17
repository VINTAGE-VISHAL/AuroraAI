"""Models representing execution logs, environments, and hyperparameter configurations."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from aurora.models.training_enums import (
    AdapterStrategy,
    OptimizerType,
    Precision,
    SchedulerType,
    TrainingRunStatus,
)


class EnvironmentSnapshot(BaseModel):
    """Immutable record tracking runtime execution package versions and hardware configurations."""
    model_config = ConfigDict(frozen=True)

    python_version: str
    torch_version: str
    transformers_version: str
    peft_version: str
    datasets_version: str
    cuda_version: Optional[str] = None
    gpu_name: Optional[str] = None
    device_count: int = 0
    os: str


class TrainingConfig(BaseModel):
    """Immutable configuration detailing hyperparameter options and strategies."""
    model_config = ConfigDict(frozen=True)

    base_model_id: str
    tokenizer_id: str
    adapter_strategy: AdapterStrategy
    lora_r: int = 8
    lora_alpha: int = 16
    lora_dropout: float = 0.05
    learning_rate: float
    batch_size: int
    epochs: int
    precision: Precision
    optimizer: OptimizerType
    scheduler: SchedulerType
    seed: int = 42


class TrainingRun(BaseModel):
    """Immutable execution log representing details of a training experiment."""
    model_config = ConfigDict(frozen=True)

    run_id: UUID
    dataset_release_id: UUID
    base_model_revision: str
    training_config: TrainingConfig
    environment: EnvironmentSnapshot
    random_seed: int
    start_time: datetime
    end_time: Optional[datetime] = None
    status: TrainingRunStatus
    metrics: Dict[str, float] = Field(default_factory=dict)
    adapter_id: Optional[UUID] = None
    checkpoint_paths: List[str] = Field(default_factory=list)
