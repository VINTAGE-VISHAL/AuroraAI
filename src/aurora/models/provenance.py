"""Provenance tracking schemas mapping data lineage across pipelines."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from aurora.models.enums import DocumentState


class FrameworkInfo(BaseModel):
    """Immutable model mapping system and runtime framework metadata details."""
    model_config = ConfigDict(frozen=True)

    framework_name: str = "AuroraEngine"
    framework_version: str = "0.1.0"
    module_name: str
    module_version: str


class PipelineProvenance(BaseModel):
    """Immutable tracking schema mapping origin component execution runs."""
    model_config = ConfigDict(frozen=True)

    stage: DocumentState
    producer: str
    timestamp: datetime
    framework: FrameworkInfo
    run_id: Optional[UUID] = None
    execution_id: Optional[UUID] = None
