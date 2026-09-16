"""Unit tests for the AdapterPackager Phase D packaging component."""

import json
import os
from datetime import timedelta
from aurora.models import ComputeDType, EvaluationResult, RawTrainingOutput, TrainingConfig
from aurora.training.adapter_packager import AdapterPackager
from aurora.training.mocks import MockModelObj, MockTokenizerObj


def test_adapter_packager_success(tmp_path) -> None:
    """Verify that AdapterPackager successfully saves model artifacts and creates metadata."""
    t_config = TrainingConfig(
        model_name="MockModel",
        tokenizer_name="MockModel",
        dataset_path="dataset.jsonl",
        output_dir=str(tmp_path / "output"),
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
        metrics={"train_loss": 0.22},
        final_loss=0.22,
        training_time=timedelta(seconds=15.0),
    )

    evaluation = EvaluationResult(
        loss=0.25,
        perplexity=1.28,
        evaluation_time=timedelta(seconds=2.0),
        passed=True,
    )

    packager = AdapterPackager()
    result = packager.package(raw_output, evaluation, t_config)

    assert result.success is True
    assert result.final_loss == 0.22
    assert os.path.exists(os.path.join(result.adapter_path, "adapter_model.safetensors"))
    assert os.path.exists(os.path.join(result.adapter_path, "adapter_config.json"))
    assert os.path.exists(os.path.join(result.adapter_path, "metadata.json"))

    # Verify metadata content
    with open(os.path.join(result.adapter_path, "metadata.json"), "r", encoding="utf-8") as f:
        meta = json.load(f)
        assert meta["base_model"] == "MockModel"
        assert meta["final_loss"] == 0.22
        assert meta["evaluation_loss"] == 0.25
        assert meta["evaluation_perplexity"] == 1.28
        assert meta["evaluation_passed"] is True
