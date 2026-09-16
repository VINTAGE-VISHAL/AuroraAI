"""Contract definition for documents within AuroraEngine."""

class DocumentContract:
    """Defines requirements, preconditions, postconditions, and invariants for documents.

    Invariants:
        1. A document must possess a unique string identifier (doc_id).
        2. Ingested contents cannot be empty after processing.
        3. Metadata must exist and contain at least: 'source_path', 'file_type', and 'char_count'.
        4. The character count field must exactly match the length of the content.

    Preconditions:
        - Ingestion source path must be valid and readable.

    Postconditions:
        - The document object is immutable or has stable hash unless content explicitly changes.
    """
    REQUIRED_METADATA_FIELDS = {"source_path", "file_type", "char_count"}
