"""Interfaces, contexts, and protocols for Swappable Training Backends."""

from typing import Any, Dict, Protocol

from pydantic import BaseModel, ConfigDict, Field

from aurora.models import DatasetRelease, TrainingRun
from aurora.models.training_run import TrainingConfig


class DatasetPrepContext(BaseModel):
    """Context holding intermediate datasets and tokenization states during preparation."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    release: DatasetRelease
    formatted_prompts: list[str] = Field(default_factory=list)
    tokenized_datasets: Any = None


class ModelPrepContext(BaseModel):
    """Context wrapping loaded model and injected strategy adapter structures."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    config: TrainingConfig
    model: Any = None


class ITrainingBackend(Protocol):
    """Interface defining pluggable backpropagation trainers."""

    def train(
        self,
        dataset: Any,
        config: TrainingConfig,
        run: TrainingRun,
    ) -> Dict[str, float]:
        """Executes optimization loops and returns evaluated run metrics."""
        ...
