"""End-to-End Integration test verifying the Document Intelligence Phase B pipeline."""

import datetime
import uuid

from aurora.models import (
    ArtifactMetadata,
    FrameworkInfo,
    PipelineProvenance,
    RawDocument,
)
from aurora.models.enums import DocumentState
from aurora.models.metadata import FileMetadata
from aurora.preprocessing.extractors import (
    DefaultEquationExtractor,
    DefaultFigureExtractor,
    DefaultTableExtractor,
)
from aurora.preprocessing.reading_order import ReadingOrderResolver
from aurora.preprocessing.segmenter import PageSegmenter


def test_end_to_end_conversion_pipeline() -> None:
    """Verifies loader, segmenter, extractors, and graph resolver flow as a single system."""
    doc_id = str(uuid.uuid4())
    prov = PipelineProvenance(
        stage=DocumentState.LOADED,
        producer="IntegrationLoader",
        timestamp=datetime.datetime.now(datetime.timezone.utc),
        framework=FrameworkInfo(module_name="Loader", module_version="1.0"),
    )
    meta = FileMetadata(source_path="file:///test.pdf", file_type="pdf", char_count=100)
    art = ArtifactMetadata(
        artifact_id=uuid.uuid4(), checksum="hash", created_at=prov.timestamp
    )

    raw_doc = RawDocument(
        doc_id=doc_id,
        source_id=doc_id,
        uri="file:///test.pdf",
        content_bytes=b"PDF bytes",
        content_hash="hash",
        state=DocumentState.LOADED,
        metadata=meta,
        provenance=prov,
        artifact=art,
    )

    # 1. Page Segmentation
    segmenter = PageSegmenter()
    page_layouts = segmenter.segment(raw_doc)
    assert len(page_layouts) == 1
    page = page_layouts[0]

    # 2. Layout Extraction
    table_extractor = DefaultTableExtractor()
    tables = table_extractor.extract(b"dummy_data", page_number=page.page_number)
    object.__setattr__(page, "tables", tables)

    figure_extractor = DefaultFigureExtractor()
    figures = figure_extractor.extract(b"dummy_data", page_number=page.page_number)
    object.__setattr__(page, "figures", figures)

    equation_extractor = DefaultEquationExtractor()
    equations = equation_extractor.extract(b"dummy_data", page_number=page.page_number)
    object.__setattr__(page, "equations", equations)

    # 3. Reading Order Resolution
    resolver = ReadingOrderResolver()
    layout_graph = resolver.resolve(page)
    object.__setattr__(page, "graph", layout_graph)

    # 4. Coverage Audits and Schema Invariants
    assert page.page_number == 1
    assert page.page_width == 612.0
    assert len(page.tables) == 1
    assert len(page.figures) == 1
    assert len(page.equations) == 1

    # Graph Traversal Integrity
    assert len(page.graph.reading_order) == 3
    assert len(page.graph.edges) == 2
    assert page.graph.root_node_id is not None

    # Bounding Box Boundaries Checks
    for table in page.tables:
        assert table.bbox is not None
        assert table.bbox.x1 < table.bbox.x2
        assert table.bbox.y1 < table.bbox.y2
        assert table.bbox.page_number == page.page_number
