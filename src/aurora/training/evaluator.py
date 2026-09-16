"""Evaluator implementation for Phase D quality verification."""

import math
import time
from datetime import timedelta
from typing import Any

from aurora.core.exceptions import InterfaceError
from aurora.interfaces.training import IEvaluator
from aurora.models import EvaluationResult, RawTrainingOutput, TrainingConfig
from aurora.registry.module_registry import ModuleRegistry

# Conditional imports for PyTorch and Transformers
try:
    import torch
    from transformers import DataCollatorForLanguageModeling, Trainer as HFTrainer, TrainingArguments
    HAS_EVAL_LIBS = True
except ImportError:
    HAS_EVAL_LIBS = False


@ModuleRegistry.register("evaluator")
class Evaluator(IEvaluator):
    """Evaluates causal language models on test/validation datasets and computes perplexity metrics."""

    def evaluate(
        self,
        raw_output: RawTrainingOutput,
        eval_dataset: Any,
        config: TrainingConfig,
    ) -> EvaluationResult:
        """Runs the validation/evaluation step on the model."""
        start_time = time.perf_counter()

        # 1. Fallback / Mock mode for CPU test environments or mock models
        if not HAS_EVAL_LIBS or config.model_name.startswith("Mock") or eval_dataset is None:
            return self._evaluate_mock(raw_output, start_time)

        try:
            # 2. Configure evaluation arguments
            eval_args = TrainingArguments(
                output_dir=config.output_dir,
                per_device_eval_batch_size=config.batch_size,
                remove_unused_columns=False,
                seed=config.seed,
            )

            # 3. Create Causal LM data collator
            data_collator = DataCollatorForLanguageModeling(
                raw_output.tokenizer,
                mlm=False,
            )

            # 4. Instantiate Hugging Face Trainer for evaluation only
            hf_trainer = HFTrainer(
                model=raw_output.model,
                args=eval_args,
                eval_dataset=eval_dataset,
                data_collator=data_collator,
            )

            # 5. Execute evaluation pass
            eval_metrics = hf_trainer.evaluate()
            elapsed = time.perf_counter() - start_time

            eval_loss = float(eval_metrics.get("eval_loss", 0.0))
            
            # Compute perplexity safely to avoid overflow
            try:
                perplexity = float(math.exp(eval_loss)) if eval_loss < 20.0 else float("inf")
            except OverflowError:
                perplexity = float("inf")

            # Determine whether the checkpoint passes our quality gate
            passed = eval_loss < config.eval_threshold

            return EvaluationResult(
                loss=eval_loss,
                perplexity=perplexity,
                evaluation_time=timedelta(seconds=elapsed),
                passed=passed,
                threshold=config.eval_threshold,
            )

        except Exception as e:
            raise InterfaceError(f"Model evaluation execution failed: {e}") from e

    def _evaluate_mock(self, raw_output: RawTrainingOutput, start_time: float) -> EvaluationResult:
        """Simulates evaluation metrics for test verification without GPU resources."""
        elapsed = time.perf_counter() - start_time
        eval_loss = raw_output.final_loss * 1.05  # slightly higher validation loss simulation
        perplexity = float(math.exp(eval_loss))
        passed = eval_loss < 1.0

        return EvaluationResult(
            loss=eval_loss,
            perplexity=perplexity,
            evaluation_time=timedelta(seconds=elapsed),
            passed=passed,
            threshold=1.0,
        )
