"""Unit tests verifying Milestone 4 LayoutGraph reading order resolutions."""

import datetime
import uuid

from aurora.models import (
    BoundingBox,
    DocumentObjectId,
    ExtractionProvenance,
    FigureUnderstanding,
    LayoutNodeType,
    LayoutRelationship,
    PageLayout,
    ProcessingStage,
    StructuredTable,
)
from aurora.preprocessing.reading_order import ReadingOrderResolver


def test_reading_order_two_column_sort() -> None:
    """Verify that ReadingOrderResolver sequences columns left-to-right then top-to-bottom."""
    doc_id = uuid.uuid4()
    prov = ExtractionProvenance(
        extractor_name="LayoutParser",
        extractor_version="1.0",
        timestamp=datetime.datetime.now(datetime.timezone.utc),
        processing_stage=ProcessingStage.SEGMENTATION,
        confidence=0.95,
    )

    # 1. Left column, lower down (y1=300)
    left_lower_id = DocumentObjectId(
        document_id=doc_id,
        page_number=1,
        object_type=LayoutNodeType.TABLE,
        local_id=uuid.uuid4(),
    )
    left_lower = StructuredTable(
        object_id=left_lower_id,
        bbox=BoundingBox(page_number=1, x1=10.0, y1=300.0, x2=200.0, y2=400.0),
        provenance=prov,
        cells=[],
        columns_count=0,
        rows_count=0,
    )

    # 2. Right column, upper up (y1=100)
    right_upper_id = DocumentObjectId(
        document_id=doc_id,
        page_number=1,
        object_type=LayoutNodeType.FIGURE,
        local_id=uuid.uuid4(),
    )
    right_upper = FigureUnderstanding(
        object_id=right_upper_id,
        bbox=BoundingBox(page_number=1, x1=400.0, y1=100.0, x2=550.0, y2=200.0),
        provenance=prov,
        caption="Right Top Figure",
    )

    # 3. Left column, upper up (y1=50)
    left_upper_id = DocumentObjectId(
        document_id=doc_id,
        page_number=1,
        object_type=LayoutNodeType.TABLE,
        local_id=uuid.uuid4(),
    )
    left_upper = StructuredTable(
        object_id=left_upper_id,
        bbox=BoundingBox(page_number=1, x1=10.0, y1=50.0, x2=200.0, y2=150.0),
        provenance=prov,
        cells=[],
        columns_count=0,
        rows_count=0,
    )

    # Mock Graph placeholder
    graph_id = DocumentObjectId(
        document_id=doc_id,
        page_number=1,
        object_type=LayoutNodeType.LIST,
        local_id=uuid.uuid4(),
    )

    from aurora.models import LayoutGraph
    empty_graph = LayoutGraph(
        graph_id=graph_id,
        nodes={},
        edges=[],
        reading_order=[],
        root_node_id=graph_id,
    )

    page = PageLayout(
        page_id=graph_id,
        page_number=1,
        page_width=612.0,
        page_height=792.0,
        graph=empty_graph,
        tables=[left_lower, left_upper],
        figures=[right_upper],
        equations=[],
    )

    resolver = ReadingOrderResolver()
    graph = resolver.resolve(page)

    # Sequence must be:
    # 1. Left upper (x=10, y=50)
    # 2. Left lower (x=10, y=300)
    # 3. Right upper (x=400, y=100)
    assert graph.reading_order == [
        left_upper_id.local_id,
        left_lower_id.local_id,
        right_upper_id.local_id,
    ]

    # Edge relationship linkage
    assert len(graph.edges) == 2
    assert graph.edges[0].relationship == LayoutRelationship.FOLLOWED_BY
    assert graph.edges[0].source_id == left_upper_id
    assert graph.edges[0].target_id == left_lower_id
    assert graph.root_node_id == left_upper_id
