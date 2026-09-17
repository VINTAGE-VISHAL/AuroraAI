"""Models representing structured and logically parsed tabular structures."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from aurora.models.layout.base import LayoutObject
from aurora.models.layout.provenance import BoundingBox


class TableCell(BaseModel):
    """An individual cell block within a structured table grid."""
    model_config = ConfigDict(frozen=True)

    row_index: int
    column_index: int
    row_span: int = 1
    col_span: int = 1
    content: str
    is_header: bool = False
    logical_row_header: Optional[str] = None
    logical_column_header: Optional[str] = None
    bbox: Optional[BoundingBox] = None


class StructuredTable(LayoutObject):
    """Grid matrix representing logically formatted tables."""
    model_config = ConfigDict(frozen=True)

    caption: Optional[str] = None
    cells: List[TableCell]
    columns_count: int
    rows_count: int
