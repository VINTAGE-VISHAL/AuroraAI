"""TrainingPipeline orchestrator for Phase D QLoRA adaptation."""

from typing import Any, List

from aurora.core.exceptions import InterfaceError
from aurora.interfaces.training import (
    IAdapterPackager,
    ICheckpointManager,
    IDatasetLoader,
    IEvaluator,
    ITrainer,
    ITrainingInputAdapter,
)
from aurora.models import (
    CheckpointInfo,
    EvaluationResult,
    ExportResult,
    TrainingConfig,
    TrainingResult,
)
from aurora.registry.module_registry import ModuleRegistry


@ModuleRegistry.register("training_pipeline")
class TrainingPipeline:
    """Coordinates Phase D pipelines adapting configs, loading datasets, optimizing, and deploying weights."""

    def __init__(
        self,
        training_input_adapter: ITrainingInputAdapter,
        trainer: ITrainer,
        checkpoint_manager: ICheckpointManager,
        evaluator: IEvaluator,
        adapter_packager: IAdapterPackager,
    ) -> None:
        self.training_input_adapter = training_input_adapter
        self.trainer = trainer
        self.checkpoint_manager = checkpoint_manager
        self.evaluator = evaluator
        self.adapter_packager = adapter_packager

    def execute(
        self,
        export_result: ExportResult,
        config: TrainingConfig,
        eval_dataset: Any = None,
        keep_last_checkpoints: int = 3,
    ) -> TrainingResult:
        """Executes the end-to-end training, checkpointing, evaluation, and packaging pipeline."""
        try:
            # 1. Adapt ExportResult and TrainingConfig -> TrainingInput
            training_input = self.training_input_adapter.adapt(export_result, config)

            # 2. Run trainer (loads dataset, model, tokenizes and executes the optimization loop)
            raw_output = self.trainer.run(training_input)

            # 3. Scan for checkpoints saved during the training loop
            checkpoints = self.checkpoint_manager.scan(config.output_dir)

            # 4. Evaluate the trained model
            evaluation_result = self.evaluator.evaluate(raw_output, eval_dataset, config)

            # 5. Package the final deployment artifacts
            packaged_result = self.adapter_packager.package(raw_output, evaluation_result, config)

            # 6. Prune old checkpoints to manage disk space
            self.checkpoint_manager.prune(checkpoints, keep_last=keep_last_checkpoints)

            # 7. Update package results with collected checkpoint metadata
            final_result = TrainingResult(
                success=packaged_result.success,
                config=packaged_result.config,
                adapter_path=packaged_result.adapter_path,
                tokenizer_path=packaged_result.tokenizer_path,
                checkpoints=checkpoints,
                evaluation=packaged_result.evaluation,
                training_time=packaged_result.training_time,
                final_loss=packaged_result.final_loss,
            )

            return final_result

        except Exception as e:
            raise InterfaceError(f"Training pipeline execution failed: {e}") from e
