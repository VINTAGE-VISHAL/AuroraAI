"""Models and Enums for the Extraction Subsystem."""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from aurora.core.artifact import ArtifactMetadata
from aurora.models.document import PipelineProvenance
from aurora.models.metadata import FileMetadata


class DocumentType(str, Enum):
    """Supported document formats inside the extraction pipeline."""
    PDF = "PDF"
    DOCX = "DOCX"
    TXT = "TXT"
    MARKDOWN = "MARKDOWN"
    HTML = "HTML"
    EPUB = "EPUB"
    PPTX = "PPTX"
    XLSX = "XLSX"
    ZIP = "ZIP"
    IMAGE = "IMAGE"
    UNKNOWN = "UNKNOWN"


class DetectionMethod(str, Enum):
    """Technique used to identify the document format signature."""
    MAGIC_BYTES = "MAGIC_BYTES"
    HEURISTIC = "HEURISTIC"
    FALLBACK = "FALLBACK"


class DocumentDescriptor(BaseModel):
    """Immutable classification description of a RawDocument."""
    model_config = ConfigDict(frozen=True)

    doc_type: DocumentType
    confidence: float
    method: DetectionMethod
    signature: Optional[str] = None


class ExtractorCapability(str, Enum):
    """Capabilities supported by an extractor plugin."""
    TEXT = "TEXT"
    TABLES = "TABLES"
    IMAGES = "IMAGES"
    METADATA = "METADATA"


class ExtractorMetadata(BaseModel):
    """Immutable metadata descriptor detailing extractor features."""
    model_config = ConfigDict(frozen=True)

    supported_type: DocumentType
    version: str
    capabilities: set[ExtractorCapability] = Field(default_factory=set)


class ExtractedDocument(BaseModel):
    """Cleaned plain-text extraction result representing EXTRACTED state."""
    model_config = ConfigDict(frozen=True)

    doc_id: str
    text: str
    tables: List[dict] = Field(default_factory=list)
    images: List[dict] = Field(default_factory=list)
    links: List[str] = Field(default_factory=list)
    metadata: FileMetadata
    provenance: PipelineProvenance
    artifact: ArtifactMetadata
