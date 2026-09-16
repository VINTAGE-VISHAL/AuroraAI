"""Unit tests verifying PageSegmenter properties and page metadata initializations."""

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
from aurora.preprocessing.segmenter import PageSegmenter


def test_page_segmenter_initialization() -> None:
    """Verify that PageSegmenter populates metadata and initializes empty structures."""
    doc_id = str(uuid.uuid4())
    prov = PipelineProvenance(
        stage=DocumentState.LOADED,
        producer="TestLoader",
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

    segmenter = PageSegmenter()
    page_layouts = segmenter.segment(raw_doc)

    assert len(page_layouts) == 1
    page = page_layouts[0]
    assert page.page_number == 1
    assert page.page_width == 612.0
    assert page.page_height == 792.0
    assert page.rotation == 0
    assert page.language == "en"

    # Verify empty collections
    assert len(page.tables) == 0
    assert len(page.figures) == 0
    assert len(page.equations) == 0
    assert len(page.graph.nodes) == 0
