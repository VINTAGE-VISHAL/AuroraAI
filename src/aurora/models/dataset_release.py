"""Models for immutable release packages of generated datasets."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from aurora.core.artifact import ArtifactMetadata
from aurora.models.dataset_statistics import DatasetStatistics


class DatasetRelease(BaseModel):
    """Immutable release manifest pointing to physical file URIs and reproducibility metadata."""
    model_config = ConfigDict(frozen=True)

    release_id: UUID
    dataset_uri: str  # URI where the file (e.g. JSONL, Parquet) is stored
    graph_version: str
    generator_version: str
    validation_version: str
    created_at: datetime
    statistics: DatasetStatistics
    checksum: str
    artifact: ArtifactMetadata
