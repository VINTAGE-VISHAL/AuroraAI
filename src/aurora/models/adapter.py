"""Models representing fine-tuned adapter artifacts and parameters."""

from typing import Dict
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from aurora.core.artifact import ArtifactMetadata


class AdapterDescriptor(BaseModel):
    """Immutable metadata descriptor outlining fine-tuned parameter weights and reference inputs."""
    model_config = ConfigDict(frozen=True)

    adapter_id: UUID
    training_run_id: UUID
    dataset_release_id: UUID
    base_model: str
    base_model_revision: str
    parameter_count: int
    trainable_parameter_count: int
    lora_r: int
    lora_alpha: int
    evaluation_summary: Dict[str, float]
    artifact: ArtifactMetadata
