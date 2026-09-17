"""Runtime File Management Interfaces.

Defines contracts for validation, storage, and orchestration of conversation-scoped
runtime educational resources.
"""

from abc import ABC, abstractmethod
from typing import Optional

from aurora.models.file_metadata import RuntimeFileMetadata, RuntimeFileResponse


class IFileValidator(ABC):
    """Behavioral contract for validating incoming files before storage."""

    @abstractmethod
    def validate(
        self,
        filename: str,
        content_type: Optional[str],
        size_bytes: int,
        conversation_id: str,
    ) -> None:
        """Validates filename, extension, content type, size, and conversation id.

        Raises:
            FileValidationError or specific subclasses upon failure.
        """
        pass

    @abstractmethod
    def validate_stream_header(self, header_bytes: bytes, extension: str) -> None:
        """Validates binary magic headers (e.g. %PDF- or ZIP header for DOCX).

        Raises:
            FileValidationError if content does not match expected format headers.
        """
        pass


class IFileStorage(ABC):
    """Behavioral contract for isolated runtime file storage and retrieval."""

    @abstractmethod
    def save_file(
        self,
        conversation_id: str,
        file_id: str,
        original_filename: str,
        content: bytes,
    ) -> str:
        """Persists uploaded file bytes in isolated conversation storage and returns storage path."""
        pass

    @abstractmethod
    def save_metadata(self, metadata: RuntimeFileMetadata) -> None:
        """Persists metadata record alongside the file."""
        pass

    @abstractmethod
    def get_metadata(
        self,
        file_id: str,
        conversation_id: Optional[str] = None,
    ) -> Optional[RuntimeFileMetadata]:
        """Retrieves stored metadata. If conversation_id is provided, enforces ownership."""
        pass

    @abstractmethod
    def delete_file(
        self,
        file_id: str,
        conversation_id: Optional[str] = None,
    ) -> bool:
        """Deletes file, metadata, and directory safely. Returns True if deleted, False if not found."""
        pass


class IFileService(ABC):
    """Application service contract coordinating validation, storage, and metadata lifecycle."""

    @abstractmethod
    def upload_file(
        self,
        conversation_id: str,
        filename: str,
        content_type: Optional[str],
        content: bytes,
    ) -> RuntimeFileResponse:
        """Coordinates validation, file ID generation, storage, and metadata creation."""
        pass

    @abstractmethod
    def get_file(
        self,
        file_id: str,
        conversation_id: Optional[str] = None,
    ) -> RuntimeFileResponse:
        """Retrieves file metadata without exposing internal filesystem paths."""
        pass

    @abstractmethod
    def delete_file(
        self,
        file_id: str,
        conversation_id: Optional[str] = None,
    ) -> bool:
        """Coordinates deletion of uploaded runtime files and their Module 01 metadata."""
        pass
