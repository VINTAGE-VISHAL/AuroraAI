"""Mock training backend for unit testing and dry runs without GPU dependencies."""

import random
from typing import Any, Dict

from aurora.models import TrainingRun
from aurora.models.training_run import TrainingConfig
from aurora.training.interfaces import ITrainingBackend


class MockTrainingBackend(ITrainingBackend):
    """Mock trainer executor simulating epoch loops and metric variations."""

    def train(
        self,
        dataset: Any,
        config: TrainingConfig,
        run: TrainingRun,
    ) -> Dict[str, float]:
        """Returns mock evaluation metrics simulating successful convergence."""
        random.seed(config.seed)
        return {
            "loss": round(random.uniform(0.1, 0.5), 4),
            "perplexity": round(random.uniform(1.1, 1.8), 4),
            "grounding_score": round(random.uniform(0.9, 1.0), 4),
            "concept_coverage": round(random.uniform(0.85, 1.0), 4),
            "exact_match": round(random.uniform(0.8, 0.95), 4),
        }
