"""Unit tests for the Evaluator Phase D quality gate component."""

import pytest
from datetime import timedelta
from aurora.models import ComputeDType, RawTrainingOutput, TrainingConfig
from aurora.training.evaluator import Evaluator
from aurora.training.mocks import MockModelObj, MockTokenizerObj


def test_evaluator_mock_evaluation() -> None:
    """Verify that Evaluator correctly calculates metrics and perplexity in mock mode."""
    t_config = TrainingConfig(
        model_name="MockModel",
        tokenizer_name="MockModel",
        dataset_path="dataset.jsonl",
        output_dir="output",
        epochs=1,
        batch_size=1,
        gradient_accumulation_steps=1,
        learning_rate=2e-5,
        warmup_ratio=0.0,
        weight_decay=0.0,
        max_seq_length=128,
        seed=42,
        lora_r=4,
        lora_alpha=8,
        lora_dropout=0.0,
        target_modules=["q"],
        load_in_4bit=False,
        bnb_compute_dtype=ComputeDType.FLOAT32,
        bf16=True,
        fp16=False,
        gradient_checkpointing=False,
        save_steps=5,
        logging_steps=1,
        eval_steps=5,
    )

    raw_output = RawTrainingOutput(
        model=MockModelObj(t_config),
        tokenizer=MockTokenizerObj(),
        metrics={"train_loss": 0.20},
        final_loss=0.20,
        training_time=timedelta(seconds=1.0),
    )

    evaluator = Evaluator()
    result = evaluator.evaluate(raw_output, eval_dataset=None, config=t_config)

    assert result.loss == pytest.approx(0.21)  # 0.20 * 1.05
    assert result.perplexity > 1.0
    assert result.passed is True
    assert result.evaluation_time >= timedelta(seconds=0)
