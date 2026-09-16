"""Unit tests for the DatasetLoader Phase D component."""

import json
import pytest
from datasets import Dataset

from aurora.core.exceptions import InterfaceError
from aurora.models import ComputeDType, ExportFormat, TrainingConfig, TrainingInput
from aurora.training.dataset_loader import DatasetLoader


def test_dataset_loader_success(tmp_path) -> None:
    """Verify loading and validating a correct JSONL file works successfully."""
    dataset_file = tmp_path / "train.jsonl"
    
    # Write mock samples
    sample1_id = "a" * 64
    sample2_id = "b" * 64
    samples = [
        {"sample_id": sample1_id, "sequence_number": 1, "payload": {"text": "Hello world"}},
        {"sample_id": sample2_id, "sequence_number": 2, "payload": {"messages": [{"role": "user", "content": "hi"}]}},
    ]
    with open(dataset_file, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s) + "\n")

    t_config = TrainingConfig(
        model_name="MockModel",
        tokenizer_name="MockModel",
        dataset_path=str(dataset_file),
        output_dir=str(tmp_path / "output"),
        epochs=1,
        batch_size=2,
        gradient_accumulation_steps=1,
        learning_rate=2e-5,
        warmup_ratio=0.0,
        weight_decay=0.01,
        max_seq_length=10,
        seed=42,
        lora_r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        target_modules=["q_proj"],
        load_in_4bit=True,
        bnb_compute_dtype=ComputeDType.FLOAT16,
        bf16=False,
        fp16=True,
        gradient_checkpointing=False,
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

    loader = DatasetLoader()
    hf_dataset, prepared = loader.load(t_input)

    assert prepared.sample_count == 2
    assert prepared.checksum == "hash_xyz"
    assert prepared.dataset_path == str(dataset_file)

    assert isinstance(hf_dataset, Dataset)
    assert len(hf_dataset) == 2
    assert hf_dataset.column_names == ["sample_id", "sequence_number", "payload"]
    assert hf_dataset[0]["sample_id"] == sample1_id
    assert hf_dataset[0]["payload"]["text"] == "Hello world"


def test_dataset_loader_invalid_schema(tmp_path) -> None:
    """Verify loading raises InterfaceError on malformed JSONL files."""
    dataset_file = tmp_path / "invalid.jsonl"
    
    # Valid sample ID, but missing payload key
    samples = [{"sample_id": "a" * 64, "sequence_number": 1}]
    with open(dataset_file, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s) + "\n")

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

    t_input = TrainingInput(
        dataset_path=str(dataset_file),
        config=t_config,
        sample_count=1,
        checksum="hash_abc",
        export_format=ExportFormat.JSONL,
    )

    loader = DatasetLoader()
    with pytest.raises(InterfaceError, match="Field required"):
        loader.load(t_input)
