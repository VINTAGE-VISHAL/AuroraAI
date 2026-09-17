from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from aurora.core.artifact import ArtifactMetadata
from aurora.models.enums import DocumentState
from aurora.models.metadata import FileMetadata
from aurora.models.provenance import PipelineProvenance
from aurora.models.segment import DocumentSegment


class RawDocument(BaseModel):
    """Raw loaded immutable binary data combined with origin metadata."""
    model_config = ConfigDict(frozen=True)

    doc_id: str
    source_id: str
    uri: str
    content_bytes: bytes
    content_hash: str
    state: DocumentState = DocumentState.LOADED
    metadata: FileMetadata
    provenance: PipelineProvenance
    artifact: ArtifactMetadata


class NormalizedDocument(BaseModel):
    """Normalized structured plain text document representing NORMALIZED state."""
    model_config = ConfigDict(frozen=True)

    doc_id: str
    text: str
    tables: List[dict] = Field(default_factory=list)
    images: List[dict] = Field(default_factory=list)
    links: List[str] = Field(default_factory=list)
    metadata: FileMetadata
    provenance: PipelineProvenance
    artifact: ArtifactMetadata


class ProcessedDocument(BaseModel):
    """Cleaned, chunked text content prepared for knowledge extraction."""
    doc_id: str
    parent_doc_id: str
    chunk_index: int
    content: str
    keywords: List[str]
    metadata: FileMetadata
    summary: Optional[str] = None


class StructuredDocument(BaseModel):
    """Immutable segmented document holding logically separated document parts."""
    model_config = ConfigDict(frozen=True)

    doc_id: str
    segments: List[DocumentSegment]
    metadata: FileMetadata
    provenance: PipelineProvenance
    artifact: ArtifactMetadata


class ExtractedDocument(BaseModel):
    """Typed wrapper model representing parsed, unnormalized PDF pages."""
    model_config = ConfigDict(frozen=True)

    doc_id: str
    uri: str
    pages: List[str]
    metadata: FileMetadata
    provenance: PipelineProvenance
    artifact: ArtifactMetadata



