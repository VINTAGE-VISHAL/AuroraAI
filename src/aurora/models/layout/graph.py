"""Models representing adjacency graphs of layout structures."""

from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from aurora.models.layout.enums import LayoutNodeType, LayoutRelationship, SemanticRole
from aurora.models.layout.provenance import BoundingBox, DocumentObjectId


class LayoutNode(BaseModel):
    """Layout block node in the document layout traversal graph."""
    model_config = ConfigDict(frozen=True)

    node_id: DocumentObjectId
    type: LayoutNodeType
    text_content: Optional[str] = None
    semantic_role: Optional[SemanticRole] = None
    bbox: Optional[BoundingBox] = None


class LayoutEdge(BaseModel):
    """Directional edge mapping spatial flows between layout nodes."""
    model_config = ConfigDict(frozen=True)

    source_id: DocumentObjectId
    target_id: DocumentObjectId
    relationship: LayoutRelationship


class LayoutGraph(BaseModel):
    """Adjacency graph detailing structural relationships and reading sequences."""
    model_config = ConfigDict(frozen=True)

    graph_id: DocumentObjectId
    nodes: Dict[UUID, LayoutNode]
    edges: List[LayoutEdge]
    reading_order: List[UUID]
    root_node_id: DocumentObjectId
