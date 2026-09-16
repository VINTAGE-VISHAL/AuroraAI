"""TokenizerService implementation for Phase D."""

from typing import Any, Dict, List
from datasets import Dataset

from aurora.interfaces.training import ITokenizerService
from aurora.models import TrainingConfig


class TokenizerService(ITokenizerService):
    """Encodes prepared training datasets using Hugging Face tokenizers deterministically."""

    def tokenize(
        self,
        hf_dataset: Dataset,
        tokenizer: Any,
        config: TrainingConfig,
    ) -> Dataset:
        """Translates message structures and text payloads into token IDs and attention masks."""
        max_seq_length = config.max_seq_length

        def tokenize_function(examples: Dict[str, Any]) -> Dict[str, Any]:
            tokenized_inputs: List[List[int]] = []
            attention_masks: List[List[int]] = []
            labels: List[List[int]] = []

            for payload in examples["payload"]:
                # 1. Format content (ChatML templates or Plain Text)
                if "messages" in payload:
                    messages = payload["messages"]
                    if hasattr(tokenizer, "apply_chat_template"):
                        text = tokenizer.apply_chat_template(messages, tokenize=False)
                    else:
                        # Fallback simple template formatting if no template exists on tokenizer
                        text = ""
                        for msg in messages:
                            text += f"<|im_start|>{msg['role']}\n{msg['content']}<|im_end|>\n"
                else:
                    text = payload["text"]

                # 2. Tokenize with truncation
                tokenized = tokenizer(
                    text,
                    truncation=True,
                    max_length=max_seq_length,
                    padding=False,
                )

                input_ids = tokenized["input_ids"]
                attention_mask = tokenized.get("attention_mask", [1] * len(input_ids))

                tokenized_inputs.append(input_ids)
                attention_masks.append(attention_mask)
            return {
                "input_ids": tokenized_inputs,
                "attention_mask": attention_masks,
            }

        tokenized_dataset = hf_dataset.map(
            tokenize_function,
            batched=True,
            remove_columns=hf_dataset.column_names,
            desc="Tokenizing dataset",
        )
        print(f"Tokenized dataset columns: {tokenized_dataset.column_names}")
        return tokenized_dataset
