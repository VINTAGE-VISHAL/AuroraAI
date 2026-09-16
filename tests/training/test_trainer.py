"""Unit tests for the QLoRA Trainer Phase D component."""

from datetime import timedelta
import pytest
from datasets import Dataset

from aurora.core.exceptions import InterfaceError
from aurora.models import ComputeDType, ExportFormat, PreparedDataset, TrainingConfig, TrainingInput
from aurora.training.adapter import TrainingInputAdapter
from aurora.training.dataset_loader import DatasetLoader
from aurora.training.model_preparer import ModelPreparer
from aurora.training.tokenizer_service import TokenizerService
from aurora.training.trainer import Trainer


def test_trainer_run_mock_success(tmp_path) -> None:
    """Verify that Trainer runs the full optimization workflow utilizing mock/fallbacks successfully."""
    dataset_file = tmp_path / "dataset.jsonl"
    dataset_file.touch()

    t_config = TrainingConfig(
        model_name="MockModel",
        tokenizer_name="MockModel",
        dataset_path=str(dataset_file),
        output_dir=str(tmp_path / "output"),
        epochs=3,
        batch_size=4,
        gradient_accumulation_steps=1,
        learning_rate=2e-4,
        warmup_ratio=0.03,
        weight_decay=0.01,
        max_seq_length=128,
        seed=42,
        lora_r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        target_modules=["q_proj"],
        load_in_4bit=True,
        bnb_compute_dtype=ComputeDType.FLOAT16,
        bf16=False,
        fp16=True,
        gradient_checkpointing=True,
        save_steps=10,
        logging_steps=1,
        eval_steps=10,
    )

    t_input = TrainingInput(
        dataset_path=str(dataset_file),
        config=t_config,
        sample_count=2,
        checksum="hash_xyz",
        export_format=ExportFormat.JSONL,
    )

    # Instantiate orchestrator components
    dataset_loader = DatasetLoader()
    tokenizer_service = TokenizerService()
    model_preparer = ModelPreparer()

    trainer = Trainer(
        dataset_loader=dataset_loader,
        tokenizer_service=tokenizer_service,
        model_preparer=model_preparer,
    )

    # Let's mock out _load_jsonl since the dataset file is empty
    def mock_load_jsonl(path):
        from aurora.models.training_corpus import SerializedSample
        return [
            SerializedSample(
                sample_id="a" * 64,
                sequence_number=1,
                payload={"text": "hello"}
            )
        ]
    dataset_loader._load_jsonl = mock_load_jsonl

    result = trainer.run(t_input)

    assert result.model is not None
    assert result.tokenizer is not None
    assert result.final_loss == 0.25
    assert result.metrics == {"train_loss": 0.25}
    assert result.training_time > timedelta(seconds=0)
