"""Shared Enums defining system boundaries and states."""

from enum import Enum


class DocumentState(str, Enum):
    """The formal processing states a document transitions through in the pipeline."""
    DISCOVERED = "DISCOVERED"
    REGISTERED = "REGISTERED"
    LOADED = "LOADED"
    EXTRACTED = "EXTRACTED"
    NORMALIZED = "NORMALIZED"
    SEGMENTED = "SEGMENTED"


class SegmentType(str, Enum):
    """Supported logical and structural content blocks for educational chunking."""
    HEADING = "HEADING"
    PARAGRAPH = "PARAGRAPH"
    LIST = "LIST"
    TABLE = "TABLE"
    CODE_BLOCK = "CODE_BLOCK"
    FIGURE = "FIGURE"
    FIGURE_CAPTION = "FIGURE_CAPTION"
    QUOTE = "QUOTE"
    FOOTNOTE = "FOOTNOTE"
    METADATA = "METADATA"

