"""Unit tests for the Training Orchestrator Pipeline Subsystem."""

import json
import os
import pytest
from datetime import timedelta

from aurora.models import (
    ComputeDType,
    ExportFormat,
    ExportResult,
    TrainingConfig,
)
from aurora.training.adapter import TrainingInputAdapter
from aurora.training.adapter_packager import AdapterPackager
from aurora.training.checkpoint_manager import CheckpointManager
from aurora.training.dataset_loader import DatasetLoader
from aurora.training.evaluator import Evaluator
from aurora.training.model_preparer import ModelPreparer
from aurora.training.pipeline import TrainingPipeline
from aurora.training.tokenizer_service import TokenizerService
from aurora.training.trainer import Trainer


def test_studio_training_orchestrator_execution(tmp_path) -> None:
    """Verify end-to-end studio training pipeline workflow using a mock backend executor."""
    dataset_file = tmp_path / "dataset.jsonl"
    
    # Write mock samples with valid SHA256 hex IDs
    sample1_id = "a" * 64
    sample2_id = "b" * 64
    samples = [
        {"sample_id": sample1_id, "sequence_number": 1, "payload": {"text": "hello"}},
        {"sample_id": sample2_id, "sequence_number": 2, "payload": {"text": "world"}},
    ]
    with open(dataset_file, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s) + "\n")

    # Phase C ExportResult mock
    from datetime import datetime, timezone, timedelta
    export_result = ExportResult(
        output_path=str(dataset_file),
        format=ExportFormat.JSONL,
        documents_exported=2,
        samples_exported=2,
        bytes_written=100,
        checksum="c" * 64,
        export_timestamp=datetime.now(timezone.utc),
        export_duration=timedelta(seconds=1.0),
    )

    t_config = TrainingConfig(
        model_name="MockModel",
        tokenizer_name="MockModel",
        dataset_path=str(dataset_file),
        output_dir=str(tmp_path / "output"),
        epochs=1,
        batch_size=1,
        gradient_accumulation_steps=1,
        learning_rate=2e-5,
        warmup_ratio=0.0,
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

    # Initialize components
    adapter = TrainingInputAdapter()
    dataset_loader = DatasetLoader()
    tokenizer_service = TokenizerService()
    model_preparer = ModelPreparer()
    trainer = Trainer(
        dataset_loader=dataset_loader,
        tokenizer_service=tokenizer_service,
        model_preparer=model_preparer,
    )
    checkpoint_manager = CheckpointManager()
    evaluator = Evaluator()
    packager = AdapterPackager()

    pipeline = TrainingPipeline(
        training_input_adapter=adapter,
        trainer=trainer,
        checkpoint_manager=checkpoint_manager,
        evaluator=evaluator,
        adapter_packager=packager,
    )

    # Execute
    result = pipeline.execute(export_result, t_config, eval_dataset=None)

    assert result.success is True
    assert result.final_loss == 0.25
    assert result.evaluation.passed is True
    assert os.path.exists(os.path.join(result.adapter_path, "metadata.json"))
