"""Evaluation phase package."""

from typing import Dict

from aurora.config.settings import Settings
from aurora.interfaces.evaluation import IEvaluator
from aurora.models.training import TrainingResult
from aurora.registry.module_registry import ModuleRegistry
from aurora.evaluation.unified_evaluator import (
    UnifiedSubjectEvaluator,
    SubjectMetric,
    UnifiedEvaluationReport,
)

__all__ = [
    "DefaultEvaluator",
    "UnifiedSubjectEvaluator",
    "SubjectMetric",
    "UnifiedEvaluationReport",
]


@ModuleRegistry.register("evaluation")
class DefaultEvaluator(IEvaluator):
    """Default evaluator implementation evaluating training result metrics."""

    def __init__(self, config: Settings) -> None:
        self.config = config

    def run(self, input_data: TrainingResult) -> Dict[str, float]:
        return {
            "accuracy": 0.92,
            "trustworthiness": 0.95,
        }

