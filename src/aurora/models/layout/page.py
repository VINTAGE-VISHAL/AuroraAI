"""Models representing metadata and elements of a page."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from aurora.models.layout.equation import MathExpression
from aurora.models.layout.figure import FigureUnderstanding
from aurora.models.layout.graph import LayoutGraph
from aurora.models.layout.provenance import DocumentObjectId
from aurora.models.layout.table import StructuredTable


class PageLayout(BaseModel):
    """Metadata container grouping all structured elements on a page."""
    model_config = ConfigDict(frozen=True)

    page_id: DocumentObjectId
    page_number: int = Field(ge=1)
    page_width: float
    page_height: float
    rotation: int = 0
    language: Optional[str] = "en"
    graph: LayoutGraph
    tables: List[StructuredTable] = Field(default_factory=list)
    figures: List[FigureUnderstanding] = Field(default_factory=list)
    equations: List[MathExpression] = Field(default_factory=list)
