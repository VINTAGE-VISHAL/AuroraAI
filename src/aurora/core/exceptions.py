"""AuroraEngine Core Exception Hierarchy."""

class AuroraError(Exception):
    """Base exception for all AuroraEngine errors."""
    pass


class ConfigurationError(AuroraError):
    """Raised when there is an issue with application configuration."""
    pass


class RegistryError(AuroraError):
    """Raised when module registry lookup or registration fails."""
    pass


class InterfaceError(AuroraError):
    """Raised when an interface contract constraint is violated."""
    pass


class StorageError(AuroraError):
    """Base exception for storage backend failures."""
    pass


class PipelineError(AuroraError):
    """Raised when pipeline orchestration fails."""
    pass


class DuplicateSourceError(AuroraError):
    """Raised when registering a source with a duplicate identity."""
    pass


class SourceNotFoundError(AuroraError):
    """Raised when a queried source does not exist."""
    pass


class InvalidSourceError(AuroraError):
    """Raised when a source format, path, or properties are invalid."""
    pass


class IngestionError(AuroraError):
    """Base exception for all ingestion-related failures."""
    pass


class DocumentLoadError(IngestionError):
    """Raised when a source document fails to load."""
    pass


class UnsupportedDocumentError(IngestionError):
    """Raised when a document type is unsupported by the loader."""
    pass


class UnreadableDocumentError(IngestionError):
    """Raised when a file exists but is unreadable or corrupted."""
    pass


class PermissionDeniedError(IngestionError):
    """Raised when reading a file fails due to permission errors."""
    pass


class ExtractionError(AuroraError):
    """Base exception for all document extraction-related failures."""
    pass


class UnsupportedExtractionError(ExtractionError):
    """Raised when no extractor is registered for a given document type."""
    pass


class ExtractionFailedError(ExtractionError):
    """Raised when document extraction process crashes."""
    pass


class CorruptedDocumentError(ExtractionError):
    """Raised when document parsing fails due to payload corruption."""
    pass


class DecoderError(ExtractionError):
    """Raised when text decoding fails."""
    pass


class NormalizationError(AuroraError):
    """Base exception for all document normalization failures."""
    pass


class InvalidNormalizationError(NormalizationError):
    """Raised when input parameters or documents are invalid for normalization."""
    pass


class UnsupportedNormalizationError(NormalizationError):
    """Raised when a requested normalization operation/step is unsupported."""
    pass


class NormalizationFailedError(NormalizationError):
    """Raised when the text normalization pipeline crashes."""
    pass


class SegmentationError(AuroraError):
    """Base exception for all document structural segmentation failures."""
    pass


class SegmentationFailedError(SegmentationError):
    """Raised when document segmentation pipeline execution crashes."""
    pass


class InvalidSegmentError(SegmentationError):
    """Raised when a segment violates integrity checks or contains cyclic links."""
    pass


class TaxonomyError(AuroraError):
    """Base exception for all concept taxonomy failures."""
    pass


class DuplicateConceptError(TaxonomyError):
    """Raised when a concept is registered multiple times under matching keys/aliases."""
    pass


class EmptyConceptError(TaxonomyError):
    """Raised when a concept lacks a name or metadata."""
    pass


class InvalidTaxonomyError(TaxonomyError):
    """Raised when a taxonomy node configuration violates structural constraints."""
    pass


class GraphConstructionError(AuroraError):
    """Base exception for all knowledge graph assembly errors."""
    pass


class InvalidGraphReferenceError(GraphConstructionError):
    """Raised when relationship or mapping references a non-existent node ID."""
    pass


class FileValidationError(AuroraError):
    """Base exception for runtime file validation failures."""
    pass


class UnsupportedFileTypeError(FileValidationError):
    """Raised when uploaded file has an unsupported extension or MIME type."""
    pass


class FileTooLargeError(FileValidationError):
    """Raised when uploaded file exceeds maximum configured size limit."""
    pass


class InvalidFilenameError(FileValidationError):
    """Raised when uploaded filename is empty, malformed, or attempts traversal."""
    pass


class InvalidConversationIdError(FileValidationError):
    """Raised when conversation ID is empty, malformed, or attempts traversal."""
    pass


class RuntimeFileNotFoundError(StorageError):
    """Raised when a runtime uploaded file is not found in storage."""
    pass


class StorageOperationError(StorageError):
    """Raised when writing, reading, or deleting runtime files encounters an I/O error."""
    pass







