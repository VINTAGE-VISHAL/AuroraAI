"""Reading Order Resolver sorting page elements into sequential LayoutGraphs."""

from typing import Dict, List
from uuid import UUID

from aurora.models import (
    LayoutEdge,
    LayoutGraph,
    LayoutNode,
    LayoutRelationship,
)
from aurora.models.layout.page import PageLayout


class ReadingOrderResolver:
    """Sorter sequencing page elements into correct layout reading flows."""

    def resolve(self, page: PageLayout) -> LayoutGraph:
        """Processes elements on page and builds the LayoutGraph mapping relationships."""
        # 1. Collect all elements to sort
        # Since Milestone 2 PageLayout has page_id and graph initialized with empty structures,
        # we can read objects (tables, figures, equations) on page and sort them.
        nodes_list: List[LayoutNode] = []

        # Convert structured layout objects to graph nodes
        for t in page.tables:
            nodes_list.append(
                LayoutNode(
                    node_id=t.object_id,
                    type=t.object_id.object_type,
                    bbox=t.bbox,
                )
            )
        for f in page.figures:
            nodes_list.append(
                LayoutNode(
                    node_id=f.object_id,
                    type=f.object_id.object_type,
                    bbox=f.bbox,
                )
            )
        for eq in page.equations:
            nodes_list.append(
                LayoutNode(
                    node_id=eq.object_id,
                    type=eq.object_id.object_type,
                    bbox=eq.bbox,
                )
            )

        # 2. Multi-column Heuristic Sort:
        # Split into columns based on x coordinate center (page_width / 2.0)
        col_mid = page.page_width / 2.0
        left_col: List[LayoutNode] = []
        right_col: List[LayoutNode] = []

        for node in nodes_list:
            if node.bbox:
                # If node centers on left side
                center_x = (node.bbox.x1 + node.bbox.x2) / 2.0
                if center_x < col_mid:
                    left_col.append(node)
                else:
                    right_col.append(node)
            else:
                left_col.append(node)

        # Sort columns vertically (by y1 coordinate)
        left_col.sort(key=lambda n: n.bbox.y1 if n.bbox else 0.0)
        right_col.sort(key=lambda n: n.bbox.y1 if n.bbox else 0.0)

        # Final ordered sequence
        sorted_nodes = left_col + right_col
        reading_order = [n.node_id.local_id for n in sorted_nodes]

        # 3. Build Adjacency Nodes Dict & Edges list
        nodes_dict: Dict[UUID, LayoutNode] = {}
        edges: List[LayoutEdge] = []

        for node in sorted_nodes:
            nodes_dict[node.node_id.local_id] = node

        # Link sequential nodes together via FOLLOWED_BY edges
        for idx in range(len(sorted_nodes) - 1):
            edges.append(
                LayoutEdge(
                    source_id=sorted_nodes[idx].node_id,
                    target_id=sorted_nodes[idx + 1].node_id,
                    relationship=LayoutRelationship.FOLLOWED_BY,
                )
            )

        root_id = page.page_id
        if sorted_nodes:
            root_id = sorted_nodes[0].node_id

        return LayoutGraph(
            graph_id=page.page_id,
            nodes=nodes_dict,
            edges=edges,
            reading_order=reading_order,
            root_node_id=root_id,
        )
