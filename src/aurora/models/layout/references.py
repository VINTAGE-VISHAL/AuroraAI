"""Models mapping cross-link references across segments."""

from pydantic import BaseModel, ConfigDict, Field

from aurora.models.layout.enums import ReferenceType
from aurora.models.layout.provenance import DocumentObjectId


class CrossReference(BaseModel):
    """Navigable links associating text segments to reference targets."""
    model_config = ConfigDict(frozen=True)

    reference_id: DocumentObjectId
    source_object_id: DocumentObjectId
    target_object_id: DocumentObjectId
    reference_type: ReferenceType
    confidence: float = Field(ge=0.0, le=1.0)
