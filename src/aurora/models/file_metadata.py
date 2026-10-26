"""Runtime File Metadata and API Data Models."""

from enum import Enum
from pydantic import BaseModel, Field


class FileStatus(str, Enum):
    """Lifecycle status of a runtime uploaded document."""
    UPLOADING = "uploading"
    STORED = "stored"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    DELETED = "deleted"


class RuntimeFileMetadata(BaseModel):
    """Comprehensive metadata model representing a runtime uploaded file in storage."""
    file_id: str = Field(description="Unique runtime file identifier, e.g. file_xxx")
    conversation_id: str = Field(description="Associated conversation session identifier")
    filename: str = Field(description="Original sanitized uploaded filename")
    content_type: str = Field(description="Verified MIME / content type")
    size_bytes: int = Field(description="File size in bytes", ge=0)
    extension: str = Field(description="Normalized lower-case extension including dot, e.g. .pdf")
    status: FileStatus = Field(default=FileStatus.STORED, description="Current lifecycle state")
    created_at: float = Field(description="Epoch timestamp when the file was registered")
    storage_path: str = Field(description="Internal relative storage path")


class RuntimeFileResponse(BaseModel):
    """Client-facing DTO that excludes internal storage paths for security."""
    file_id: str
    conversation_id: str
    filename: str
    content_type: str
    size_bytes: int
    extension: str
    status: str
    created_at: float

    @classmethod
    def from_metadata(cls, meta: RuntimeFileMetadata) -> "RuntimeFileResponse":
        return cls(
            file_id=meta.file_id,
            conversation_id=meta.conversation_id,
            filename=meta.filename,
            content_type=meta.content_type,
            size_bytes=meta.size_bytes,
            extension=meta.extension,
            status=meta.status.value if isinstance(meta.status, FileStatus) else str(meta.status),
            created_at=meta.created_at,
        )


class ExtractedFileResponse(BaseModel):
    """Structured response detailing runtime extraction results for downstream modules."""
    file_id: str
    conversation_id: str
    filename: str
    extension: str
    status: str
    text: str
    char_count: int
    page_count: int = 0
    pages: list[str] = Field(default_factory=list)
    has_content: bool = True


class CleanupResult(BaseModel):
    """Summary of automatic file and vector cleanup operations."""
    cleaned_files_count: int = 0
    cleaned_vectors_count: int = 0
    scanned_conversations_count: int = 0
    stale_files: list[str] = Field(default_factory=list)
    skipped_in_use_count: int = 0
    errors: list[str] = Field(default_factory=list)


