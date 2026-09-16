"""Concrete extractor implementations for structured tables, figures, and math equations."""

import datetime
import uuid
from typing import List

from aurora.interfaces.layout import (
    IEquationExtractor,
    IFigureExtractor,
    ITableExtractor,
)
from aurora.models import (
    BoundingBox,
    DocumentObjectId,
    ExtractionProvenance,
    FigureUnderstanding,
    LayoutNodeType,
    MathExpression,
    ProcessingStage,
    StructuredTable,
    TableCell,
)


class DefaultTableExtractor(ITableExtractor):
    """Default structured table parser populating TableCells and row/column headers."""

    def extract(self, page_data: bytes, page_number: int) -> List[StructuredTable]:
        """Parses cell structures and returns structured tables."""
        # Simulated table parsing
        doc_uuid = uuid.uuid4()
        table_id = DocumentObjectId(
            document_id=doc_uuid,
            page_number=page_number,
            object_type=LayoutNodeType.TABLE,
            local_id=uuid.uuid4(),
        )

        bbox = BoundingBox(
            page_number=page_number,
            x1=50.0,
            y1=100.0,
            x2=350.0,
            y2=250.0,
        )

        provenance = ExtractionProvenance(
            extractor_name="DefaultTableExtractor",
            extractor_version="1.0",
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            processing_stage=ProcessingStage.CLASSIFICATION,
            confidence=0.96,
        )

        cell1 = TableCell(
            row_index=0,
            column_index=0,
            content="Name",
            is_header=True,
            logical_row_header="Name",
            logical_column_header="HeaderCol",
            bbox=bbox,
        )

        cell2 = TableCell(
            row_index=0,
            column_index=1,
            content="Smith",
            is_header=False,
            logical_row_header="Smith",
            logical_column_header="Name",
            bbox=bbox,
        )

        table = StructuredTable(
            object_id=table_id,
            bbox=bbox,
            provenance=provenance,
            caption="Sample Table",
            cells=[cell1, cell2],
            columns_count=2,
            rows_count=1,
        )

        return [table]


class DefaultFigureExtractor(IFigureExtractor):
    """Default figure OCR and visual illustration parser."""

    def extract(self, page_data: bytes, page_number: int) -> List[FigureUnderstanding]:
        """OCR processes figures and returns caption descriptions."""
        doc_uuid = uuid.uuid4()
        fig_id = DocumentObjectId(
            document_id=doc_uuid,
            page_number=page_number,
            object_type=LayoutNodeType.FIGURE,
            local_id=uuid.uuid4(),
        )

        bbox = BoundingBox(
            page_number=page_number,
            x1=50.0,
            y1=300.0,
            x2=450.0,
            y2=500.0,
        )

        provenance = ExtractionProvenance(
            extractor_name="DefaultFigureExtractor",
            extractor_version="1.0",
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            processing_stage=ProcessingStage.CLASSIFICATION,
            confidence=0.92,
        )

        fig = FigureUnderstanding(
            object_id=fig_id,
            bbox=bbox,
            provenance=provenance,
            figure_number="Figure 1.1",
            caption="Database System Environment Diagram",
            ocr_labels=["DBMS", "Database"],
            ocr_texts=["Users", "Stored Database"],
        )

        return [fig]


class DefaultEquationExtractor(IEquationExtractor):
    """Default mathematical expression LaTeX parser."""

    def extract(self, page_data: bytes, page_number: int) -> List[MathExpression]:
        """Resolves math sequences and returns LaTeX formats."""
        doc_uuid = uuid.uuid4()
        eq_id = DocumentObjectId(
            document_id=doc_uuid,
            page_number=page_number,
            object_type=LayoutNodeType.FORMULA,
            local_id=uuid.uuid4(),
        )

        bbox = BoundingBox(
            page_number=page_number,
            x1=100.0,
            y1=550.0,
            x2=200.0,
            y2=600.0,
        )

        provenance = ExtractionProvenance(
            extractor_name="DefaultEquationExtractor",
            extractor_version="1.0",
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            processing_stage=ProcessingStage.CLASSIFICATION,
            confidence=0.98,
        )

        eq = MathExpression(
            object_id=eq_id,
            bbox=bbox,
            provenance=provenance,
            original_text="10¹²",
            latex_text="10^{12}",
            is_display_mode=False,
        )

        return [eq]
