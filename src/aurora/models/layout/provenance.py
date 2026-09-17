"""Models defining coordinates, identifiers, and extraction provenance."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aurora.models.layout.enums import LayoutNodeType, ProcessingStage


class BoundingBox(BaseModel):
    """Spatial coordinates bounding box on a specific document page."""
    model_config = ConfigDict(frozen=True)

    page_number: int = Field(ge=1)
    x1: float
    y1: float
    x2: float
    y2: float

    @model_validator(mode="after")
    def validate_coordinates(self) -> "BoundingBox":
        """Verify bounding box dimensions are valid."""
        if self.x1 >= self.x2:
            raise ValueError("x1 must be strictly less than x2")
        if self.y1 >= self.y2:
            raise ValueError("y1 must be strictly less than y2")
        return self


class DocumentObjectId(BaseModel):
    """Stable multi-part unique identifier for any layout or document element."""
    model_config = ConfigDict(frozen=True)

    document_id: UUID
    page_number: int
    object_type: LayoutNodeType
    local_id: UUID


class ExtractionProvenance(BaseModel):
    """Auditing metadata identifying extraction tools and validation confidence."""
    model_config = ConfigDict(frozen=True)

    extractor_name: str
    extractor_version: str
    timestamp: datetime
    processing_stage: ProcessingStage
    confidence: float = Field(ge=0.0, le=1.0)
