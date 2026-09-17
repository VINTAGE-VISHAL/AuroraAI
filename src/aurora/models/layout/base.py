"""Base model abstraction for layout elements."""

from typing import Optional

from pydantic import BaseModel, ConfigDict

from aurora.models.layout.provenance import BoundingBox, DocumentObjectId, ExtractionProvenance


class LayoutObject(BaseModel):
    """Common base class for all structural layout elements on a page."""
    model_config = ConfigDict(frozen=True)

    object_id: DocumentObjectId
    bbox: Optional[BoundingBox] = None
    provenance: ExtractionProvenance
