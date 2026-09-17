"""Runtime File Storage component.

Provides isolated, conversation-scoped filesystem storage for runtime educational uploads.
Enforces that uploads are strictly stored under `data/runtime_uploads/<conversation_id>/<file_id>/`
and NEVER in `data/corpus/`, `data/raw/`, or `data/output/`.
"""

import json
import os
import shutil
from pathlib import Path
from typing import Optional

from aurora.config.paths import get_project_root
from aurora.config.settings import RuntimeStorageConfig
from aurora.core.exceptions import (
    InvalidConversationIdError,
    InvalidFilenameError,
    RuntimeFileNotFoundError,
    StorageOperationError,
)
from aurora.interfaces.runtime_file import IFileStorage
from aurora.models.file_metadata import RuntimeFileMetadata


class RuntimeFileStorage(IFileStorage):
    """Secure filesystem storage manager for runtime conversation documents."""

    def __init__(
        self,
        config: Optional[RuntimeStorageConfig] = None,
        base_dir: Optional[Path] = None,
    ) -> None:
        self.config = config or RuntimeStorageConfig()
        if base_dir is not None:
            self.base_dir = Path(base_dir).resolve()
        else:
            root = get_project_root()
            self.base_dir = (root / self.config.upload_dir).resolve()

        # Ensure base upload directory exists
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_target_dir(self, conversation_id: str, file_id: str) -> Path:
        """Computes and validates target directory ensuring no traversal outside base_dir."""
        # Sanitize identifiers
        if not conversation_id or ".." in conversation_id or "/" in conversation_id or "\\" in conversation_id:
            raise InvalidConversationIdError("Invalid conversation identifier")
        if not file_id or ".." in file_id or "/" in file_id or "\\" in file_id:
            raise StorageOperationError("Invalid file identifier")

        target_dir = (self.base_dir / conversation_id / file_id).resolve()

        # Strict containment check
        try:
            target_dir.relative_to(self.base_dir)
        except ValueError:
            raise StorageOperationError("Path traversal attempt detected in storage path.")

        return target_dir

    def save_file(
        self,
        conversation_id: str,
        file_id: str,
        original_filename: str,
        content: bytes,
    ) -> str:
        """Saves file content to isolated directory and returns relative storage path."""
        target_dir = self._get_target_dir(conversation_id, file_id)
        target_dir.mkdir(parents=True, exist_ok=True)

        _, ext = os.path.splitext(original_filename)
        ext_lower = ext.lower()
        file_name = f"original_file{ext_lower}"
        target_file = target_dir / file_name

        try:
            with open(target_file, "wb") as f:
                f.write(content)
        except Exception as e:
            raise StorageOperationError(f"Failed to write file to storage: {e}") from e

        # Return path relative to base_dir or project root
        return str(target_file.relative_to(self.base_dir).as_posix())

    def save_metadata(self, metadata: RuntimeFileMetadata) -> None:
        """Persists metadata as metadata.json inside the file directory."""
        target_dir = self._get_target_dir(metadata.conversation_id, metadata.file_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        meta_file = target_dir / "metadata.json"

        try:
            with open(meta_file, "w", encoding="utf-8") as f:
                f.write(metadata.model_dump_json(indent=2))
        except Exception as e:
            raise StorageOperationError(f"Failed to save file metadata: {e}") from e

    def get_metadata(
        self,
        file_id: str,
        conversation_id: Optional[str] = None,
    ) -> Optional[RuntimeFileMetadata]:
        """Retrieves stored metadata. If conversation_id is known, locates directly.
        Otherwise, searches within base_dir.
        """
        if conversation_id:
            target_dir = self._get_target_dir(conversation_id, file_id)
            meta_file = target_dir / "metadata.json"
            if meta_file.is_file():
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        return RuntimeFileMetadata.model_validate(data)
                except Exception as e:
                    raise StorageOperationError(f"Error reading file metadata: {e}") from e
            return None

        # If conversation_id is not specified, scan conversation directories
        if not self.base_dir.exists():
            return None

        for conv_dir in self.base_dir.iterdir():
            if conv_dir.is_dir():
                target_dir = conv_dir / file_id
                meta_file = target_dir / "metadata.json"
                if meta_file.is_file():
                    try:
                        with open(meta_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            return RuntimeFileMetadata.model_validate(data)
                    except Exception as e:
                        raise StorageOperationError(f"Error reading file metadata: {e}") from e

        return None

    def delete_file(
        self,
        file_id: str,
        conversation_id: Optional[str] = None,
    ) -> bool:
        """Deletes file, metadata, and container directory. Enforces conversation ownership if specified."""
        meta = self.get_metadata(file_id, conversation_id)
        if not meta:
            return False

        target_dir = self._get_target_dir(meta.conversation_id, meta.file_id)
        if target_dir.exists():
            try:
                shutil.rmtree(target_dir)
                # If conversation directory is now empty, optionally clean it up
                conv_dir = target_dir.parent
                if conv_dir.exists() and not any(conv_dir.iterdir()):
                    conv_dir.rmdir()
                return True
            except Exception as e:
                raise StorageOperationError(f"Failed to delete runtime file directory: {e}") from e

        return False
