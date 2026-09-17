"""Dataset schemas for instruction fine-tuning datasets."""

from typing import List, Optional

from pydantic import BaseModel


class QAPair(BaseModel):
    """An individual question-answer instruction item."""
    instruction: str
    input_context: Optional[str] = None
    response: str
    reference_concept: str


class InstructionDataset(BaseModel):
    """Full engineered instruction-tuning dataset."""
    name: str
    pairs: List[QAPair]
    split: str  # e.g., 'train', 'validation', 'test'
