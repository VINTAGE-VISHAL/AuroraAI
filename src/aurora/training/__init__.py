"""Model training and adapter tuning orchestrator package."""

from aurora.config.settings import Settings
from aurora.interfaces.training import ITrainer
from aurora.models import TrainingInput, RawTrainingOutput
from aurora.models.training import TrainingResult
from aurora.registry.module_registry import ModuleRegistry
from aurora.training.backends.mock_backend import MockTrainingBackend
from aurora.training.dataset import DatasetPreparer
from aurora.training.evaluation import EvaluationEngine
from aurora.training.interfaces import DatasetPrepContext, ITrainingBackend, ModelPrepContext
from aurora.training.model_prep import ModelPreparer
from aurora.training.pipeline import TrainingPipeline


@ModuleRegistry.register("training")
class DefaultTrainer(ITrainer):
    """Default model fine-tuning executor."""

    def __init__(self, config: Settings) -> None:
        self.config = config

    def run(self, input_data: TrainingInput) -> RawTrainingOutput:
        from datetime import timedelta
        from aurora.models import RawTrainingOutput
        from aurora.training.mocks import MockModelObj, MockTokenizerObj

        t_config = input_data.config

        return RawTrainingOutput(
            model=MockModelObj(t_config),
            tokenizer=MockTokenizerObj(),
            metrics={"train_loss": 0.25},
            final_loss=0.25,
            training_time=timedelta(seconds=5.0),
        )


__all__ = [
    "DatasetPrepContext",
    "ModelPrepContext",
    "ITrainingBackend",
    "DatasetPreparer",
    "ModelPreparer",
    "MockTrainingBackend",
    "EvaluationEngine",
    "TrainingPipeline",
    "DefaultTrainer",
]
