"""Models for resource and source asset ingestion."""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class SourceStatus(str, Enum):
    """Execution state status for a source document."""
    ACTIVE = "ACTIVE"
    MODIFIED = "MODIFIED"
    REMOVED = "REMOVED"
    INVALID = "INVALID"
    NEW = "NEW"


class DocumentChange(str, Enum):
    """Change detection state when syncing storage directories."""
    UNCHANGED = "UNCHANGED"
    MODIFIED = "MODIFIED"
    REMOVED = "REMOVED"
    NEW = "NEW"


class SourceMetadata(BaseModel):
    """System metadata defining source properties and validation track."""
    uri: str
    size_bytes: int
    file_format: str
    checksum: str
    registered_at: float
    last_verified: float
    version: int = 1
    status: SourceStatus = SourceStatus.NEW


class SourceDocument(BaseModel):
    """Source asset tracked by the framework."""
    doc_id: str
    uri: str
    checksum: str
    subject_name: str
    metadata: SourceMetadata


class Subject(BaseModel):
    """A collection of documents mapped to an educational subject."""
    name: str
    documents: List[SourceDocument] = Field(default_factory=list)
    description: Optional[str] = None
