"""Evaluation layer contract."""

from abc import abstractmethod
from typing import Dict

from aurora.interfaces.base import IPipelineComponent
from aurora.models.training import TrainingResult


class IEvaluator(IPipelineComponent[TrainingResult, Dict[str, float]]):
    """Contract for verifying output trustworthiness and domain metric alignment."""

    @abstractmethod
    def run(self, input_data: TrainingResult) -> Dict[str, float]:
        """Evaluates model performance metrics against standard validation suites."""
        pass
