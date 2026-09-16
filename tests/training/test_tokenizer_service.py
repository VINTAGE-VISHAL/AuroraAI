"""Unit tests for the TokenizerService Phase D component."""

from datasets import Dataset
from aurora.models import ComputeDType, TrainingConfig
from aurora.training.tokenizer_service import TokenizerService


class MockTokenizer:
    """Mock Hugging Face tokenizer for validation tests."""

    def __call__(self, text, truncation=True, max_length=512, padding=False):
        # Simply return length of string as mock token IDs
        tokens = [ord(c) % 100 for c in text[:max_length]]
        return {"input_ids": tokens, "attention_mask": [1] * len(tokens)}


def test_tokenizer_service_plaintext() -> None:
    """Verify that TokenizerService encodes plain text payload lists successfully."""
    raw_data = {
        "sample_id": ["s1"],
        "sequence_number": [1],
        "payload": [{"text": "Hello world"}]
    }
    hf_dataset = Dataset.from_dict(raw_data)

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
        max_seq_length=5,
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

    service = TokenizerService()
    tokenizer = MockTokenizer()
    tokenized = service.tokenize(hf_dataset, tokenizer, t_config)

    assert len(tokenized) == 1
    assert set(tokenized.column_names) == {"input_ids", "attention_mask"}
    assert len(tokenized[0]["input_ids"]) == 5  # Enforces max_seq_length=5


def test_tokenizer_service_chatml() -> None:
    """Verify that TokenizerService encodes ChatML payload lists successfully."""
    raw_data = {
        "sample_id": ["s2"],
        "sequence_number": [2],
        "payload": [{"messages": [{"role": "user", "content": "hi"}]}]
    }
    hf_dataset = Dataset.from_dict(raw_data)

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
        gradient_checkpointing=False,
        save_steps=10,
        logging_steps=1,
        eval_steps=10,
    )

    service = TokenizerService()
    tokenizer = MockTokenizer()
    tokenized = service.tokenize(hf_dataset, tokenizer, t_config)

    assert len(tokenized) == 1
    assert len(tokenized[0]["input_ids"]) > 0
