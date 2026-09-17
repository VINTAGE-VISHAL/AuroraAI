"""Models for reporting training outcomes, quality runs, and evaluations."""

from typing import Any, Dict, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from aurora.models.training_run import TrainingRun


class TrainingReport(BaseModel):
    """Immutable quality report summarizing metrics of a training run."""
    model_config = ConfigDict(frozen=True)

    report_id: UUID
    training_run: TrainingRun
    dataset_statistics: Dict[str, Any]
    training_statistics: Dict[str, Any]
    evaluation_results: Dict[str, Any]
    adapter_summary: Dict[str, Any]
    warnings: List[str]
