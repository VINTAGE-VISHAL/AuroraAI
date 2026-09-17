"""Models defining structured statistics and quality metrics for generated datasets."""

from typing import Dict

from pydantic import BaseModel, ConfigDict


class DatasetStatistics(BaseModel):
    """Immutable calculated quality metrics and category distributions of a dataset release."""
    model_config = ConfigDict(frozen=True)

    total_examples: int
    format_distribution: Dict[str, int]
    concept_coverage: float  # Percentage of taxonomy concepts represented
    difficulty_distribution: Dict[str, int]
    knowledge_unit_coverage: float  # Percentage of KUs represented
    duplicate_rate: float
    validation_score: float
