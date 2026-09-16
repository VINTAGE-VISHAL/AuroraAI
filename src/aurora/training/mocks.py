"""Mock implementations for model preparation dry-runs and CPU testing environments."""

from typing import Any
from aurora.models import TrainingConfig


class MockTokenizerObj:
    """Mock Hugging Face tokenizer that acts like PreTrainedTokenizerBase."""

    def __init__(self) -> None:
        self.pad_token = "[PAD]"
        self.eos_token = "[EOS]"

    def __call__(self, text: str, **kwargs: Any) -> Any:
        tokens = [ord(c) % 100 for c in text]
        return {"input_ids": tokens, "attention_mask": [1] * len(tokens)}

    def apply_chat_template(self, messages: Any, **kwargs: Any) -> str:
        return str(messages)


class MockModelObj:
    """Mock Hugging Face Causal LM that acts like PreTrainedModel."""

    def __init__(self, config: TrainingConfig) -> None:
        self.config = config
        self.lora_applied = True
        self.gradient_checkpointing = config.gradient_checkpointing
        self.load_in_4bit = config.load_in_4bit

    def gradient_checkpointing_enable(self) -> None:
        self.gradient_checkpointing = True
