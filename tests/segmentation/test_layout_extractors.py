"""Unit tests verifying Milestone 3 layout objects extraction and Pydantic validators."""

from aurora.preprocessing.extractors import (
    DefaultEquationExtractor,
    DefaultFigureExtractor,
    DefaultTableExtractor,
)


def test_default_layout_extractors() -> None:
    """Verify that concrete extractors populate the corresponding models with valid data."""
    # 1. Table Extractor
    table_extractor = DefaultTableExtractor()
    tables = table_extractor.extract(b"dummy_data", page_number=1)

    assert len(tables) == 1
    table = tables[0]
    assert table.caption == "Sample Table"
    assert len(table.cells) == 2
    assert table.cells[0].logical_row_header == "Name"
    assert table.cells[1].logical_column_header == "Name"
    assert table.columns_count == 2
    assert table.rows_count == 1
    assert table.provenance.confidence == 0.96

    # 2. Figure Extractor
    figure_extractor = DefaultFigureExtractor()
    figures = figure_extractor.extract(b"dummy_data", page_number=1)

    assert len(figures) == 1
    fig = figures[0]
    assert fig.figure_number == "Figure 1.1"
    assert fig.caption == "Database System Environment Diagram"
    assert "DBMS" in fig.ocr_labels
    assert fig.provenance.confidence == 0.92

    # 3. Equation Extractor
    equation_extractor = DefaultEquationExtractor()
    equations = equation_extractor.extract(b"dummy_data", page_number=1)

    assert len(equations) == 1
    eq = equations[0]
    assert eq.original_text == "10¹²"
    assert eq.latex_text == "10^{12}"
    assert eq.provenance.confidence == 0.98
