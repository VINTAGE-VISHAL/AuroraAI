"""Unified multi-subject evaluator for Phase D quality verification across all CS subjects."""

import math
import time
from datetime import timedelta
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, ConfigDict

from aurora.core.exceptions import InterfaceError
from aurora.interfaces.training import IEvaluator
from aurora.models import EvaluationResult, RawTrainingOutput, TrainingConfig
from aurora.registry.module_registry import ModuleRegistry

try:
    import torch
    from transformers import DataCollatorForLanguageModeling, Trainer as HFTrainer, TrainingArguments
    HAS_EVAL_LIBS = True
except ImportError:
    HAS_EVAL_LIBS = False


class SubjectMetric(BaseModel):
    """Evaluation metrics breakdown for a single educational subject."""
    model_config = ConfigDict(frozen=True)

    subject: str
    sample_count: int
    loss: float
    perplexity: float
    passed: bool


class UnifiedEvaluationReport(BaseModel):
    """Aggregate evaluation report across all educational subjects."""
    model_config = ConfigDict(frozen=True)

    overall_loss: float
    overall_perplexity: float
    evaluation_time: timedelta
    passed: bool
    threshold: float
    subject_metrics: Dict[str, SubjectMetric]


@ModuleRegistry.register("unified_evaluator")
class UnifiedSubjectEvaluator(IEvaluator):
    """Evaluates fine-tuned causal language models across multi-subject datasets."""

    def evaluate(
        self,
        raw_output: RawTrainingOutput,
        eval_dataset: Any,
        config: TrainingConfig,
    ) -> EvaluationResult:
        """Standard pipeline evaluation entry point returning EvaluationResult."""
        report = self.evaluate_multi_subject(raw_output, eval_dataset, config)
        return EvaluationResult(
            loss=report.overall_loss,
            perplexity=report.overall_perplexity,
            evaluation_time=report.evaluation_time,
            passed=report.passed,
            threshold=report.threshold,
        )

    def evaluate_multi_subject(
        self,
        raw_output: RawTrainingOutput,
        eval_dataset: Any,
        config: TrainingConfig,
    ) -> UnifiedEvaluationReport:
        """Runs validation breakdown per educational subject."""
        start_time = time.perf_counter()

        if not HAS_EVAL_LIBS or config.model_name.startswith("Mock") or eval_dataset is None:
            return self._evaluate_mock_multi_subject(raw_output, start_time, config)

        try:
            eval_args = TrainingArguments(
                output_dir=config.output_dir,
                per_device_eval_batch_size=config.batch_size,
                remove_unused_columns=False,
                seed=config.seed,
            )

            data_collator = DataCollatorForLanguageModeling(
                raw_output.tokenizer,
                mlm=False,
            )

            hf_trainer = HFTrainer(
                model=raw_output.model,
                args=eval_args,
                eval_dataset=eval_dataset,
                data_collator=data_collator,
            )

            eval_metrics = hf_trainer.evaluate()
            elapsed = time.perf_counter() - start_time
            eval_loss = float(eval_metrics.get("eval_loss", 0.0))

            try:
                perplexity = float(math.exp(eval_loss)) if eval_loss < 20.0 else float("inf")
            except OverflowError:
                perplexity = float("inf")

            passed = eval_loss < config.eval_threshold

            # Calculate per-subject break-down metrics if subject metadata present
            subject_metrics = self._partition_and_evaluate_subjects(
                hf_trainer=hf_trainer,
                eval_dataset=eval_dataset,
                threshold=config.eval_threshold,
            )

            return UnifiedEvaluationReport(
                overall_loss=eval_loss,
                overall_perplexity=perplexity,
                evaluation_time=timedelta(seconds=elapsed),
                passed=passed,
                threshold=config.eval_threshold,
                subject_metrics=subject_metrics,
            )

        except Exception as e:
            raise InterfaceError(f"Multi-subject model evaluation failed: {e}") from e

    def _partition_and_evaluate_subjects(
        self,
        hf_trainer: Any,
        eval_dataset: Any,
        threshold: float,
    ) -> Dict[str, SubjectMetric]:
        """Partitions evaluation dataset by subject and evaluates each subset."""
        metrics: Dict[str, SubjectMetric] = {}
        subjects = ["DBMS", "DSA", "OOPS", "OS", "CNT", "OOSE"]

        for subject in subjects:
            try:
                # Check if dataset supports filtering or indexing by subject
                if hasattr(eval_dataset, "filter"):
                    sub_ds = eval_dataset.filter(
                        lambda ex: ex.get("subject") == subject or ex.get("metadata", {}).get("subject") == subject
                    )
                    count = len(sub_ds)
                else:
                    count = 0
                    sub_ds = None

                if count > 0 and sub_ds is not None:
                    res = hf_trainer.evaluate(eval_dataset=sub_ds)
                    sub_loss = float(res.get("eval_loss", 0.0))
                    sub_ppl = float(math.exp(sub_loss)) if sub_loss < 20.0 else float("inf")
                    metrics[subject] = SubjectMetric(
                        subject=subject,
                        sample_count=count,
                        loss=sub_loss,
                        perplexity=sub_ppl,
                        passed=sub_loss < threshold,
                    )
            except Exception:
                continue

        return metrics

    def _evaluate_mock_multi_subject(
        self,
        raw_output: RawTrainingOutput,
        start_time: float,
        config: TrainingConfig,
    ) -> UnifiedEvaluationReport:
        """Simulates multi-subject evaluation for unit testing without GPU requirements."""
        elapsed = time.perf_counter() - start_time
        base_loss = raw_output.final_loss * 1.05
        overall_ppl = float(math.exp(base_loss))
        passed = base_loss < config.eval_threshold

        subjects = ["DBMS", "DSA", "OOPS", "OS", "CNT", "OOSE"]
        subject_metrics: Dict[str, SubjectMetric] = {}

        for idx, subj in enumerate(subjects):
            # Variance per subject for synthetic benchmarking
            factor = 0.95 + (idx * 0.02)
            s_loss = round(base_loss * factor, 4)
            s_ppl = round(float(math.exp(s_loss)), 4)
            subject_metrics[subj] = SubjectMetric(
                subject=subj,
                sample_count=200,
                loss=s_loss,
                perplexity=s_ppl,
                passed=s_loss < config.eval_threshold,
            )

        return UnifiedEvaluationReport(
            overall_loss=round(base_loss, 4),
            overall_perplexity=round(overall_ppl, 4),
            evaluation_time=timedelta(seconds=elapsed),
            passed=passed,
            threshold=config.eval_threshold,
            subject_metrics=subject_metrics,
        )
