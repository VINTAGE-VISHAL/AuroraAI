"""Models linking layout structures to knowledge abstractions."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from aurora.models.layout.enums import LinkType
from aurora.models.layout.provenance import DocumentObjectId


class LayoutKnowledgeLink(BaseModel):
    """Bridge linking layout objects directly to L2 Knowledge Units."""
    model_config = ConfigDict(frozen=True)

    link_id: DocumentObjectId
    layout_object_id: DocumentObjectId
    knowledge_unit_id: UUID
    link_type: LinkType
    confidence: float
