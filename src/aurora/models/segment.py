"""Immutable models representing structural slices of a document."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from aurora.core.artifact import SourceReference
from aurora.models.document import PipelineProvenance
from aurora.models.enums import SegmentType


class DocumentSegment(BaseModel):
    """An individual logically isolated node block of document content."""
    model_config = ConfigDict(frozen=True)

    segment_id: str
    doc_id: str
    type: SegmentType
    text: str
    level: int = 0
    parent_id: Optional[str] = None
    children_ids: List[str] = Field(default_factory=list)
    start_offset: int
    end_offset: int
    segment_index: int
    provenance: PipelineProvenance
    source_reference: Optional[SourceReference] = None

