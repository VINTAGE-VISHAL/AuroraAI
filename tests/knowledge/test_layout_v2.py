"""Unit tests verifying Document Intelligence Phase A layout schemas and validation constraints."""

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from aurora.models import (
    BoundingBox,
    DocumentObjectId,
    ExtractionProvenance,
    FigureUnderstanding,
    LayoutEdge,
    LayoutGraph,
    LayoutKnowledgeLink,
    LayoutNode,
    LayoutNodeType,
    LayoutRelationship,
    LinkType,
    MathExpression,
    PageLayout,
    ProcessingStage,
    SemanticRole,
    StructuredTable,
    TableCell,
)


def test_bounding_box_validators() -> None:
    """Verify that bounding box constraints are correctly validated."""
    # Valid box
    box = BoundingBox(page_number=1, x1=0.0, y1=0.0, x2=10.0, y2=10.0)
    assert box.page_number == 1

    # Invalid coordinates x1 >= x2
    with pytest.raises(ValidationError):
        BoundingBox(page_number=1, x1=10.0, y1=0.0, x2=5.0, y2=10.0)

    # Invalid coordinates y1 >= y2
    with pytest.raises(ValidationError):
        BoundingBox(page_number=1, x1=0.0, y1=10.0, x2=10.0, y2=5.0)

    # Invalid page number < 1
    with pytest.raises(ValidationError):
        BoundingBox(page_number=0, x1=0.0, y1=0.0, x2=10.0, y2=10.0)


def test_provenance_confidence_validators() -> None:
    """Verify that extraction provenance confidence limits are enforced."""
    # Valid
    prov = ExtractionProvenance(
        extractor_name="TableExtractor",
        extractor_version="1.0",
        timestamp=datetime.now(timezone.utc),
        processing_stage=ProcessingStage.INGESTION,
        confidence=0.95,
    )
    assert prov.confidence == 0.95

    # Out of boundary confidence > 1.0
    with pytest.raises(ValidationError):
        ExtractionProvenance(
            extractor_name="TableExtractor",
            extractor_version="1.0",
            timestamp=datetime.now(timezone.utc),
            processing_stage=ProcessingStage.INGESTION,
            confidence=1.05,
        )

    # Out of boundary confidence < 0.0
    with pytest.raises(ValidationError):
        ExtractionProvenance(
            extractor_name="TableExtractor",
            extractor_version="1.0",
            timestamp=datetime.now(timezone.utc),
            processing_stage=ProcessingStage.INGESTION,
            confidence=-0.1,
        )


def test_nested_layout_models() -> None:
    """Verify nesting layout model structures, indexing, and link bridges."""
    doc_id = uuid.uuid4()
    page_id = DocumentObjectId(
        document_id=doc_id,
        page_number=1,
        object_type=LayoutNodeType.HEADING,
        local_id=uuid.uuid4(),
    )

    prov = ExtractionProvenance(
        extractor_name="LayoutParser",
        extractor_version="1.0",
        timestamp=datetime.now(timezone.utc),
        processing_stage=ProcessingStage.SEGMENTATION,
        confidence=0.98,
    )

    # Table with logical headers
    table_obj_id = DocumentObjectId(
        document_id=doc_id,
        page_number=1,
        object_type=LayoutNodeType.TABLE,
        local_id=uuid.uuid4(),
    )
    cell = TableCell(
        row_index=0,
        column_index=0,
        content="Header",
        is_header=True,
        logical_row_header="Row1",
        logical_column_header="Col1",
    )
    table = StructuredTable(
        object_id=table_obj_id,
        caption="Sample Table",
        cells=[cell],
        columns_count=1,
        rows_count=1,
        provenance=prov,
    )

    # Math expression
    math_obj_id = DocumentObjectId(
        document_id=doc_id,
        page_number=1,
        object_type=LayoutNodeType.FORMULA,
        local_id=uuid.uuid4(),
    )
    math = MathExpression(
        object_id=math_obj_id,
        original_text="10¹²",
        latex_text="10^{12}",
        provenance=prov,
    )

    # Figure understanding Level 1 details
    fig_obj_id = DocumentObjectId(
        document_id=doc_id,
        page_number=1,
        object_type=LayoutNodeType.FIGURE,
        local_id=uuid.uuid4(),
    )
    figure = FigureUnderstanding(
        object_id=fig_obj_id,
        figure_number="Figure 1.1",
        caption="DBMS Architecture",
        ocr_labels=["DBMS", "Database"],
        provenance=prov,
    )

    # Layout Graph
    graph_id = DocumentObjectId(
        document_id=doc_id,
        page_number=1,
        object_type=LayoutNodeType.LIST,
        local_id=uuid.uuid4(),
    )
    node1 = LayoutNode(
        node_id=table_obj_id,
        type=LayoutNodeType.TABLE,
        semantic_role=SemanticRole.EXAMPLE,
    )
    node2 = LayoutNode(
        node_id=fig_obj_id,
        type=LayoutNodeType.FIGURE,
        semantic_role=SemanticRole.DEFINITION,
    )
    edge = LayoutEdge(
        source_id=table_obj_id,
        target_id=fig_obj_id,
        relationship=LayoutRelationship.FOLLOWED_BY,
    )

    graph = LayoutGraph(
        graph_id=graph_id,
        nodes={table_obj_id.local_id: node1, fig_obj_id.local_id: node2},
        edges=[edge],
        reading_order=[table_obj_id.local_id, fig_obj_id.local_id],
        root_node_id=table_obj_id,
    )

    # Page layout grouping
    page = PageLayout(
        page_id=page_id,
        page_number=1,
        page_width=612.0,
        page_height=792.0,
        graph=graph,
        tables=[table],
        figures=[figure],
        equations=[math],
    )

    assert page.page_number == 1
    assert page.page_width == 612.0
    assert len(page.tables) == 1
    assert page.graph.nodes[table_obj_id.local_id].semantic_role == SemanticRole.EXAMPLE

    # Link bridge to Knowledge Unit
    ku_id = uuid.uuid4()
    link = LayoutKnowledgeLink(
        link_id=DocumentObjectId(
            document_id=doc_id,
            page_number=1,
            object_type=LayoutNodeType.PARAGRAPH,
            local_id=uuid.uuid4(),
        ),
        layout_object_id=fig_obj_id,
        knowledge_unit_id=ku_id,
        link_type=LinkType.SUPPORTS,
        confidence=0.9,
    )
    assert link.link_type == LinkType.SUPPORTS
