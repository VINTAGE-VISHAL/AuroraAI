"""Runtime File Management Interfaces.

Defines contracts for validation, storage, and orchestration of conversation-scoped
runtime educational resources.
"""

from abc import ABC, abstractmethod
from typing import Optional

from aurora.models.file_metadata import (
    CleanupResult,
    ExtractedFileResponse,
    RuntimeFileMetadata,
    RuntimeFileResponse,
)
from aurora.models.context_fusion import FusedContext, GroundedPrompt
from aurora.models.embedding import EmbeddingBatchResult
from aurora.models.retrieval import RetrievalResult
from aurora.models.runtime_chunk import ChunkingConfig, ChunkingResult
from aurora.models.vector_store import IndexingResult





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
    def read_file(
        self,
        file_id: str,
        conversation_id: Optional[str] = None,
    ) -> bytes:
        """Reads file bytes from storage. If conversation_id is provided, enforces ownership."""
        pass

    @abstractmethod
    def delete_file(
        self,
        file_id: str,
        conversation_id: Optional[str] = None,
    ) -> bool:
        """Deletes file, metadata, and directory safely. Returns True if deleted, False if not found."""
        pass

    @abstractmethod
    def list_all_metadata(self) -> list[RuntimeFileMetadata]:
        """Lists all persisted file metadata across all conversations."""
        pass

    @abstractmethod
    def delete_conversation(self, conversation_id: str) -> bool:
        """Removes the entire conversation upload directory and all contained files."""
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

    @abstractmethod
    def delete_conversation(
        self,
        conversation_id: str,
    ) -> bool:
        """Coordinates deletion of an entire conversation's files and vector collection."""
        pass

    @abstractmethod
    def cleanup_stale_files(
        self,
        max_age_hours: Optional[float] = None,
        active_conversation_ids: Optional[set[str]] = None,
    ) -> "CleanupResult":
        """Executes safe, conservative cleanup of genuinely stale/abandoned runtime files."""
        pass

    @abstractmethod
    def extract_file(
        self,
        file_id: str,
        conversation_id: Optional[str] = None,
    ) -> ExtractedFileResponse:
        """Coordinates runtime text extraction for an uploaded and stored file."""
        pass

    @abstractmethod
    def chunk_file(
        self,
        file_id: str,
        conversation_id: Optional[str] = None,
        config: Optional[ChunkingConfig] = None,
    ) -> ChunkingResult:
        """Coordinates runtime text preprocessing and chunking for a stored/extracted file."""
        pass

    @abstractmethod
    def embed_file(
        self,
        file_id: str,
        conversation_id: Optional[str] = None,
        config: Optional[ChunkingConfig] = None,
    ) -> EmbeddingBatchResult:
        """Coordinates runtime extraction, chunking, and dense vector embedding for a stored file."""
        pass

    @abstractmethod
    def index_file(
        self,
        file_id: str,
        conversation_id: Optional[str] = None,
        config: Optional[ChunkingConfig] = None,
    ) -> IndexingResult:
        """Coordinates the full pipeline: Upload -> Extract -> Chunk -> Embed -> Store in vector database."""
        pass

    @abstractmethod
    def retrieve_context(
        self,
        query: str,
        conversation_id: str,
        top_k: Optional[int] = None,
        file_id: Optional[str] = None,
    ) -> RetrievalResult:
        """Coordinates semantic retrieval of top-k relevant document chunks for Module 07 prompt context fusion."""
        pass

    @abstractmethod
    def build_rag_context(
        self,
        query: str,
        conversation_id: str,
        top_k: Optional[int] = None,
        file_id: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> FusedContext:
        """Retrieves and fuses document chunks into a structured, budget-bounded context."""
        pass

    @abstractmethod
    def assemble_grounded_prompt(
        self,
        query: str,
        conversation_id: str,
        top_k: Optional[int] = None,
        file_id: Optional[str] = None,
        max_tokens: Optional[int] = None,
        base_system_prompt: Optional[str] = None,
    ) -> GroundedPrompt:
        """Retrieves, fuses, and assembles a grounded prompt ready for LLM consumption in Module 08."""
        pass



