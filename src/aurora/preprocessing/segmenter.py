"""Page Segmenter initializing page metrics and physical layout containers."""

import uuid
from typing import List

from aurora.models import (
    DocumentObjectId,
    LayoutGraph,
    LayoutNodeType,
    PageLayout,
    RawDocument,
)


class PageSegmenter:
    """Segmenter partitioning raw document contents into empty PageLayout structures."""

    def segment(self, raw_doc: RawDocument) -> List[PageLayout]:
        """Segments raw content into PageLayout structures with initialized container lists."""
        doc_uuid = uuid.UUID(hashlib_uuid_from_str(raw_doc.doc_id))

        # Milestone 2: Simulate physical pages count based on length, or parse basic properties
        # Default to a single page block representing the PDF page flow initially
        pages_count = 1
        page_layouts: List[PageLayout] = []

        for p_num in range(1, pages_count + 1):
            page_id = DocumentObjectId(
                document_id=doc_uuid,
                page_number=p_num,
                object_type=LayoutNodeType.HEADING,
                local_id=uuid.uuid4(),
            )

            # Initialize empty graph
            graph_id = DocumentObjectId(
                document_id=doc_uuid,
                page_number=p_num,
                object_type=LayoutNodeType.LIST,
                local_id=uuid.uuid4(),
            )
            empty_graph = LayoutGraph(
                graph_id=graph_id,
                nodes={},
                edges=[],
                reading_order=[],
                root_node_id=graph_id,
            )

            layout = PageLayout(
                page_id=page_id,
                page_number=p_num,
                page_width=612.0,  # Standard Letter Width
                page_height=792.0,  # Standard Letter Height
                rotation=0,
                language="en",
                graph=empty_graph,
                tables=[],
                figures=[],
                equations=[],
            )
            page_layouts.append(layout)

        return page_layouts


def hashlib_uuid_from_str(val: str) -> str:
    """Generate a stable UUID hex string from raw content string."""
    import hashlib
    m = hashlib.md5(val.encode("utf-8"))
    return m.hexdigest()
