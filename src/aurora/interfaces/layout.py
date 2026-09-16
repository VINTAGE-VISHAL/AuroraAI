"""Interfaces defining contracts for modular layout and object extractors."""

from typing import List, Protocol

from aurora.models.layout.equation import MathExpression
from aurora.models.layout.figure import FigureUnderstanding
from aurora.models.layout.page import PageLayout
from aurora.models.layout.table import StructuredTable


class ITableExtractor(Protocol):
    """Protocol for pluggable structured table extractors."""

    def extract(self, page_data: bytes, page_number: int) -> List[StructuredTable]:
        """Parses cell coordinates and headers from raw page data."""
        ...


class IFigureExtractor(Protocol):
    """Protocol for pluggable figure OCR and label extractors."""

    def extract(self, page_data: bytes, page_number: int) -> List[FigureUnderstanding]:
        """Extracts bounding boxes, captions, and OCR texts from visual diagrams."""
        ...


class IEquationExtractor(Protocol):
    """Protocol for formula and mathematical latex extractors."""

    def extract(self, page_data: bytes, page_number: int) -> List[MathExpression]:
        """Compiles equations to LaTeX representation with confidence levels."""
        ...


class ILayoutExtractor(Protocol):
    """Protocol for page layout segmentation and reading order engines."""

    def extract(self, page_data: bytes, page_number: int) -> PageLayout:
        """Assembles layout graphs, nodes, and reading orders for a page."""
        ...
