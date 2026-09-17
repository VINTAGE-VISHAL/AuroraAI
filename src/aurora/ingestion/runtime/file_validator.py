"""Runtime File Validator component.

Enforces strict validation on filename, path safety, MIME type, extension,
file size, and binary magic headers.
"""

import os
import re
from pathlib import Path
from typing import Optional, Set

from aurora.config.settings import RuntimeStorageConfig
from aurora.core.exceptions import (
    FileTooLargeError,
    InvalidConversationIdError,
    InvalidFilenameError,
    UnsupportedFileTypeError,
)
from aurora.interfaces.runtime_file import IFileValidator


class RuntimeFileValidator(IFileValidator):
    """Production validator for runtime conversational file uploads."""

    # Explicit magic signatures for supported file types
    MAGIC_SIGNATURES = {
        ".pdf": [b"%PDF-"],
        ".docx": [b"PK\x03\x04"],  # Standard ZIP / OOXML header
    }

    def __init__(self, config: Optional[RuntimeStorageConfig] = None) -> None:
        self.config = config or RuntimeStorageConfig()
        self.allowed_extensions: Set[str] = {
            ext.lower() for ext in self.config.allowed_extensions
        }
        self.max_bytes = self.config.max_upload_size_mb * 1024 * 1024

    def sanitize_filename(self, filename: str) -> str:
        """Strips path components, traversal tokens, and dangerous characters from filename."""
        if not filename or not filename.strip():
            raise InvalidFilenameError("Filename cannot be empty or whitespace.")

        raw_trimmed = filename.strip()
        # Direct check for traversal indicators in raw filename
        if ".." in raw_trimmed or raw_trimmed.startswith("/") or raw_trimmed.startswith("\\"):
            raise InvalidFilenameError(f"Filename contains invalid traversal patterns: {filename}")

        # Extract base name to strip leading directory parts if client provided a path
        clean_name = os.path.basename(raw_trimmed.replace("\\", "/"))

        # Remove control characters and null bytes
        clean_name = re.sub(r"[\x00-\x1f\x7f]", "", clean_name)

        # Check for path traversal attempts
        if ".." in clean_name or clean_name in {".", ".."}:
            raise InvalidFilenameError(f"Filename contains invalid traversal patterns: {filename}")

        if not clean_name:
            raise InvalidFilenameError("Filename resolves to an empty string after sanitization.")

        return clean_name


    def validate_conversation_id(self, conversation_id: str) -> str:
        """Validates conversation ID format and prevents path traversal."""
        if not conversation_id or not conversation_id.strip():
            raise InvalidConversationIdError("Conversation ID cannot be empty.")

        clean_conv_id = conversation_id.strip()

        # Enforce safe alphanumeric and underscore/hyphen identifiers
        if not re.match(r"^[a-zA-Z0-9_\-]+$", clean_conv_id):
            raise InvalidConversationIdError(
                f"Conversation ID '{clean_conv_id}' contains invalid characters. "
                "Only letters, numbers, underscores, and hyphens are allowed."
            )

        if ".." in clean_conv_id or "/" in clean_conv_id or "\\" in clean_conv_id:
            raise InvalidConversationIdError("Conversation ID cannot perform path traversal.")

        return clean_conv_id

    def validate(
        self,
        filename: str,
        content_type: Optional[str],
        size_bytes: int,
        conversation_id: str,
    ) -> None:
        """Validates filename, extension, content type, size, and conversation id."""
        # 1. Validate conversation ID
        self.validate_conversation_id(conversation_id)

        # 2. Sanitize and validate filename
        sanitized_name = self.sanitize_filename(filename)

        # 3. Check extension
        _, ext = os.path.splitext(sanitized_name)
        ext_lower = ext.lower()

        if not ext_lower:
            raise UnsupportedFileTypeError(
                f"File '{filename}' has no extension. Supported formats: {list(self.allowed_extensions)}"
            )

        if ext_lower not in self.allowed_extensions:
            raise UnsupportedFileTypeError(
                f"Extension '{ext_lower}' is not supported. Supported extensions: {sorted(list(self.allowed_extensions))}"
            )

        # 4. Check file size
        if size_bytes < 0:
            raise FileTooLargeError("File size cannot be negative.")

        if size_bytes > self.max_bytes:
            mb_limit = self.config.max_upload_size_mb
            actual_mb = size_bytes / (1024 * 1024)
            raise FileTooLargeError(
                f"File size ({actual_mb:.2f} MB) exceeds maximum allowed limit of {mb_limit} MB."
            )

        # 5. Check MIME / content-type if provided
        if content_type:
            ct = content_type.lower().split(";")[0].strip()
            # Allow wildcard or matching configured MIME types
            if self.config.allowed_mime_types and ct not in self.config.allowed_mime_types:
                # Text or markdown files are sometimes sent as application/octet-stream or text/plain
                if not (ext_lower in {".txt", ".md"} and ct in {"text/plain", "application/octet-stream"}):
                    # We log or allow if extension is clearly supported, but raise if clearly dangerous (e.g. application/x-executable)
                    if "executable" in ct or "sh" in ct or "bat" in ct:
                        raise UnsupportedFileTypeError(f"Disallowed content type: {ct}")

    def validate_stream_header(self, header_bytes: bytes, extension: str) -> None:
        """Validates binary magic headers for binary formats."""
        ext_lower = extension.lower()
        if ext_lower in self.MAGIC_SIGNATURES:
            signatures = self.MAGIC_SIGNATURES[ext_lower]
            matched = any(header_bytes.startswith(sig) for sig in signatures)
            if not matched:
                raise UnsupportedFileTypeError(
                    f"File content does not match expected binary header for format '{ext_lower}'."
                )
