"""Validator for FileMetadata objects."""

from aurora.contracts.document_contract import DocumentContract
from aurora.core.exceptions import InterfaceError
from aurora.models.metadata import FileMetadata


def validate_metadata(metadata: FileMetadata) -> None:
    """Check that metadata meets DocumentContract requirements."""
    for field in DocumentContract.REQUIRED_METADATA_FIELDS:
        if not hasattr(metadata, field) or getattr(metadata, field) is None:
            raise InterfaceError(f"Metadata is missing required field: '{field}'")

    if metadata.char_count < 0:
        raise InterfaceError("Metadata char_count cannot be negative.")
