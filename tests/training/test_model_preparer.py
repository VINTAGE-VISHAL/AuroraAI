"""Unit tests for the ModelPreparer Phase D component."""

from aurora.models import ComputeDType, TrainingConfig
from aurora.training.model_preparer import ModelPreparer


def test_model_preparer_mock_fallback() -> None:
    """Verify that ModelPreparer correctly instantiates and configures mock model/tokenizer structures."""
    t_config = TrainingConfig(
        model_name="MockModel",
        tokenizer_name="MockModel",
        dataset_path="mock.jsonl",
        output_dir="output",
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

    preparer = ModelPreparer()
    model, tokenizer = preparer.prepare(t_config)

    assert model.lora_applied is True
    assert model.gradient_checkpointing is True
    assert model.load_in_4bit is True
    assert tokenizer.pad_token == "[PAD]"
    assert tokenizer.eos_token == "[EOS]"
