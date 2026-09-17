"""Runtime File Application Service.

Coordinates validation, file ID generation, storage persistence,
and metadata management for conversation-scoped educational documents.
"""

import os
import time
import uuid
from typing import Optional

from aurora.core.exceptions import RuntimeFileNotFoundError
from aurora.interfaces.runtime_file import IFileService, IFileStorage, IFileValidator
from aurora.models.file_metadata import (
    FileStatus,
    RuntimeFileMetadata,
    RuntimeFileResponse,
)


class FileService(IFileService):
    """Orchestrates runtime file upload, query, and deletion operations."""

    def __init__(
        self,
        validator: IFileValidator,
        storage: IFileStorage,
    ) -> None:
        self.validator = validator
        self.storage = storage

    def upload_file(
        self,
        conversation_id: str,
        filename: str,
        content_type: Optional[str],
        content: bytes,
    ) -> RuntimeFileResponse:
        """Coordinates:
        1. Validation (filename, size, MIME, conversation_id)
        2. Binary stream header validation
        3. Unique file ID generation
        4. Storage persistence
        5. Metadata record creation
        """
        size_bytes = len(content)

        # 1. Validate high-level properties
        self.validator.validate(
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            conversation_id=conversation_id,
        )

        _, ext = os.path.splitext(filename)
        ext_lower = ext.lower()

        # 2. Binary header validation for binary formats (e.g. %PDF-, DOCX ZIP header)
        if size_bytes > 0:
            header_sample = content[:16]
            self.validator.validate_stream_header(header_sample, ext_lower)

        # 3. Generate secure unique file ID
        file_id = f"file_{uuid.uuid4().hex[:12]}"

        # 4. Save file to conversation storage
        storage_path = self.storage.save_file(
            conversation_id=conversation_id,
            file_id=file_id,
            original_filename=filename,
            content=content,
        )

        # 5. Build and save metadata
        metadata = RuntimeFileMetadata(
            file_id=file_id,
            conversation_id=conversation_id,
            filename=os.path.basename(filename.strip()),
            content_type=content_type or "application/octet-stream",
            size_bytes=size_bytes,
            extension=ext_lower,
            status=FileStatus.STORED,
            created_at=time.time(),
            storage_path=storage_path,
        )
        self.storage.save_metadata(metadata)

        # 6. Return client-safe DTO
        return RuntimeFileResponse.from_metadata(metadata)

    def get_file(
        self,
        file_id: str,
        conversation_id: Optional[str] = None,
    ) -> RuntimeFileResponse:
        """Retrieves file metadata without exposing filesystem paths."""
        meta = self.storage.get_metadata(file_id, conversation_id)
        if not meta:
            raise RuntimeFileNotFoundError(f"File '{file_id}' was not found.")
        return RuntimeFileResponse.from_metadata(meta)

    def delete_file(
        self,
        file_id: str,
        conversation_id: Optional[str] = None,
    ) -> bool:
        """Deletes file and metadata safely."""
        deleted = self.storage.delete_file(file_id, conversation_id)
        if not deleted:
            raise RuntimeFileNotFoundError(f"File '{file_id}' was not found.")
        return True
