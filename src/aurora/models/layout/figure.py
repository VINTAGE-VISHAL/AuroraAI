"""Models representing figure elements and visual diagrams."""

from typing import List, Optional

from pydantic import ConfigDict, Field

from aurora.models.layout.base import LayoutObject


class FigureUnderstanding(LayoutObject):
    """Level 1 structured metadata for visual illustrations."""
    model_config = ConfigDict(frozen=True)

    figure_number: Optional[str] = None
    caption: Optional[str] = None
    ocr_labels: List[str] = Field(default_factory=list)
    ocr_texts: List[str] = Field(default_factory=list)
