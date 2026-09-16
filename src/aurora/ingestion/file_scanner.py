"""File Scanner implementation discovering filesystem resources."""

import hashlib
import os
import time
from pathlib import Path
from typing import List

from aurora.core.exceptions import InvalidSourceError
from aurora.interfaces.ingestion import IFileScanner
from aurora.models.source import SourceMetadata, SourceStatus


class FileScanner(IFileScanner):
    """Recursively scans a local root directory to discover documents."""

    def _calculate_checksum(self, filepath: Path) -> str:
        """Calculate the SHA256 checksum of a file in chunks."""
        sha256_hash = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                for byte_block in iter(lambda: f.read(8192), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            raise InvalidSourceError(f"Failed to read file for checksum calculation: {e}") from e

    def scan(self, root_uri: str, allowed_extensions: set[str]) -> List[SourceMetadata]:
        """Scans the local directory and returns a list of SourceMetadata."""
        root_path = Path(root_uri)
        if not root_path.exists() or not root_path.is_dir():
            raise InvalidSourceError(
                f"Root scanning directory does not exist or is not a directory: {root_uri}"
            )

        metadata_list: List[SourceMetadata] = []
        normalized_extensions = {ext.lower().lstrip(".") for ext in allowed_extensions}

        try:
            for dirpath, _, filenames in os.walk(root_path):
                dirpath_path = Path(dirpath)

                # Check for hidden directories in the path components
                relative_dir = dirpath_path.relative_to(root_path.parent)
                if any(part.startswith(".") for part in relative_dir.parts):
                    continue

                for filename in filenames:
                    if filename.startswith("."):
                        continue  # ignore hidden files

                    filepath = dirpath_path / filename
                    suffix = filepath.suffix.lower().lstrip(".")

                    if suffix in normalized_extensions:
                        try:
                            stat = filepath.stat()
                            checksum = self._calculate_checksum(filepath)

                            metadata = SourceMetadata(
                                uri=filepath.resolve().as_uri(),
                                size_bytes=stat.st_size,
                                file_format=suffix,
                                checksum=checksum,
                                registered_at=time.time(),
                                last_verified=time.time(),
                                status=SourceStatus.NEW,
                            )
                            metadata_list.append(metadata)
                        except (PermissionError, FileNotFoundError) as e:
                            # If file is deleted or lacks permissions during scan
                            raise InvalidSourceError(
                                f"Error accessing file {filepath}: {e}"
                            ) from e
        except InvalidSourceError:
            raise
        except Exception as e:
            raise InvalidSourceError(
                f"Scanning failed due to unexpected error: {e}"
            ) from e

        return metadata_list
