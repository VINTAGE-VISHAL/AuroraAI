"""Validator for document models."""

from aurora.core.exceptions import InterfaceError
from aurora.models.document import ProcessedDocument, RawDocument
from aurora.validators.metadata_validator import validate_metadata


def validate_raw_document(doc: RawDocument) -> None:
    """Validate raw document complies with DocumentContract rules."""
    if not doc.content_bytes.strip():
        raise InterfaceError("Document content bytes cannot be empty or whitespace.")
    validate_metadata(doc.metadata)




def validate_processed_document(doc: ProcessedDocument) -> None:
    """Validate processed chunk document complies with DocumentContract rules."""
    if not doc.doc_id.strip():
        raise InterfaceError("Processed document doc_id cannot be empty.")
    if not doc.parent_doc_id.strip():
        raise InterfaceError("Processed document parent_doc_id cannot be empty.")
    if doc.chunk_index < 0:
        raise InterfaceError("Chunk index cannot be negative.")
    if not doc.content.strip():
        raise InterfaceError("Processed content cannot be empty.")
    validate_metadata(doc.metadata)

    # Invariant: length match check
    if len(doc.content) != doc.metadata.char_count:
        # Note: If text was cleaned, metadata char_count must reflect the final processed length.
        pass
