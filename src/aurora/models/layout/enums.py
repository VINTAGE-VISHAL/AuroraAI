"""Enums classifying layout node types, relationships, stages, and link types."""

from enum import Enum


class LayoutNodeType(str, Enum):
    """Supported types of layout elements found on a page."""
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    FIGURE = "figure"
    FORMULA = "formula"
    LIST = "list"
    PAGE_HEADER = "page_header"
    PAGE_FOOTER = "page_footer"


class LayoutRelationship(str, Enum):
    """Hierarchical and spatial relationships between layout nodes."""
    CONTAINS = "contains"
    FOLLOWED_BY = "followed_by"
    CAPTIONED_BY = "captioned_by"


class ReferenceType(str, Enum):
    """Types of cross-references mapped within textual flows."""
    MENTIONS_FIGURE = "mentions_figure"
    SEE_SECTION = "see_section"
    SEE_CHAPTER = "see_chapter"


class ProcessingStage(str, Enum):
    """Document pipeline stage tracing metadata."""
    INGESTION = "ingestion"
    SEGMENTATION = "segmentation"
    CLASSIFICATION = "classification"


class SemanticRole(str, Enum):
    """Semantic context roles applied to layout elements."""
    DEFINITION = "definition"
    EXAMPLE = "example"
    WARNING = "warning"
    SUMMARY = "summary"
    QUESTION = "question"
    FOOTNOTE = "footnote"


class LinkType(str, Enum):
    """Categorized mapping links connecting layout elements to knowledge units."""
    REPRESENTS = "represents"
    SUPPORTS = "supports"
    DEFINES = "defines"
    EXPLAINS = "explains"
    REFERENCES = "references"
