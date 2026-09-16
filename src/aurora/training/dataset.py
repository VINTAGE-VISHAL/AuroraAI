"""Dataset preparation utilities loading, formatting, and tokenizing released training datasets."""

from typing import Any, Dict, List

from aurora.models import DatasetCollection
from aurora.training.interfaces import DatasetPrepContext


class DatasetPreparer:
    """Utility managing formatting, tokenization, and validation checks on training examples."""

    def prepare(
        self, context: DatasetPrepContext, collection: DatasetCollection
    ) -> DatasetPrepContext:
        """Processes raw dataset examples into tokenized and formatted splits."""
        formatted: List[str] = []

        # 1. Conversation Formatting
        for ex in collection.examples:
            formatted_prompt = f"Prompt: {ex.input}\nResponse: {ex.output}"
            formatted.append(formatted_prompt)

        # 2. Mock Tokenization (character count indices)
        tokenized_splits: Dict[str, Any] = {
            "train": [],
            "val": [],
        }

        # 3. Split: 80% Train, 20% Val
        split_idx = int(len(formatted) * 0.8)
        train_prompts = formatted[:split_idx]
        val_prompts = formatted[split_idx:]

        for prompt in train_prompts:
            tokenized_splits["train"].append([ord(char) for char in prompt])

        for prompt in val_prompts:
            tokenized_splits["val"].append([ord(char) for char in prompt])

        # Mutate context
        object.__setattr__(context, "formatted_prompts", formatted)
        object.__setattr__(context, "tokenized_datasets", tokenized_splits)
        return context
