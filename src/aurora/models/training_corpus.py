"""Domain models defining lossless training corpus structures."""

from datetime import datetime, timedelta
from enum import Enum
import re
from typing import List, Literal, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from aurora.core.artifact import ArtifactMetadata
from aurora.models.metadata import FileMetadata

# Regex to validate 64-character lowercase SHA256 hex string
SHA256_HEX_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class ExportFormat(str, Enum):
    """Supported file formats for exported corpus data."""
    JSONL = "jsonl"


class TrainingSampleMetadata(BaseModel):
    """Immutable typed metadata for a TrainingSample to avoid unstructured dicts."""
    model_config = ConfigDict(frozen=True)

    heading_level: Optional[int] = None
    child_count: int
    heading_text: Optional[str] = None

    @field_validator("child_count")
    @classmethod
    def child_count_must_be_non_negative(cls, v: int) -> int:
        """Ensures child_count is greater than or equal to 0."""
        if v < 0:
            raise ValueError("child_count must be >= 0.")
        return v


class TrainingSampleTraceability(BaseModel):
    """Traceability mapping back to original document and segment origins."""
    model_config = ConfigDict(frozen=True)

    doc_id: str
    heading_segment_id: Optional[str] = None
    source_segment_ids: List[str]
    page_numbers: List[int]

    @field_validator("page_numbers")
    @classmethod
    def page_numbers_must_be_sorted_and_unique(cls, v: List[int]) -> List[int]:
        """Ensures page numbers list contains unique values sorted in ascending order."""
        if len(v) != len(set(v)):
            raise ValueError("page_numbers must contain unique values.")
        if v != sorted(v):
            raise ValueError("page_numbers must be sorted in ascending order.")
        return v

    @field_validator("source_segment_ids")
    @classmethod
    def source_segment_ids_must_be_non_empty_and_unique(cls, v: List[str]) -> List[str]:
        """Ensures that there is at least one source segment and that they are unique."""
        if not v:
            raise ValueError("source_segment_ids must not be empty.")
        if len(v) != len(set(v)):
            raise ValueError("source_segment_ids must contain unique values.")
        return v


class TrainingSample(BaseModel):
    """A single training instance representing a logically grouped section.

    Invariants:
        - text must be non-empty and non-whitespace.
        - sequence_number must be >= 1.
        - sample_id must be a valid 64-char lowercase SHA256 hex string.
    """
    model_config = ConfigDict(frozen=True)

    sample_id: str
    sequence_number: int
    text: str
    traceability: TrainingSampleTraceability
    metadata: TrainingSampleMetadata

    @field_validator("text")
    @classmethod
    def text_must_not_be_empty(cls, v: str) -> str:
        """Ensures that the content text is non-empty and non-whitespace."""
        if not v.strip():
            raise ValueError("text must be non-empty and non-whitespace.")
        return v

    @field_validator("sequence_number")
    @classmethod
    def sequence_number_must_be_positive(cls, v: int) -> int:
        """Ensures sequence number is positive and starts at 1."""
        if v < 1:
            raise ValueError("sequence_number must be >= 1.")
        return v

    @field_validator("sample_id")
    @classmethod
    def sample_id_must_be_valid_sha256(cls, v: str) -> str:
        """Ensures sample ID matches 64-character lowercase SHA256 hex format."""
        if not SHA256_HEX_PATTERN.match(v):
            raise ValueError("sample_id must be a valid 64-character lowercase SHA256 hex string.")
        return v


class TrainingDocument(BaseModel):
    """Lossless representation of a single StructuredDocument converted for training."""
    model_config = ConfigDict(frozen=True)

    doc_id: str
    samples: List[TrainingSample]
    metadata: FileMetadata
    artifact: ArtifactMetadata

    @field_validator("samples")
    @classmethod
    def samples_must_not_be_empty(cls, v: List[TrainingSample]) -> List[TrainingSample]:
        """Ensures document contains at least one training sample."""
        if not v:
            raise ValueError("samples list must not be empty.")
        return v


class TrainingCorpus(BaseModel):
    """Immutable collection of TrainingDocuments constituting a complete lossless corpus."""
    model_config = ConfigDict(frozen=True)

    corpus_id: UUID
    documents: List[TrainingDocument]
    artifact: ArtifactMetadata

    @field_validator("documents")
    @classmethod
    def documents_must_not_be_empty(cls, v: List[TrainingDocument]) -> List[TrainingDocument]:
        """Ensures corpus contains at least one training document."""
        if not v:
            raise ValueError("documents list must not be empty.")
        return v


class CorpusValidationResult(BaseModel):
    """Immutable report containing details of the lossless validation checks."""
    model_config = ConfigDict(frozen=True)

    passed: bool
    samples_checked: int
    documents_checked: int
    completeness: bool
    ordering: bool
    duplication: bool
    traceability: bool
    deterministic_ids: bool
    metadata: bool
    structural_integrity: bool


class SerializedPayload(BaseModel):
    """Base Pydantic class representing a formatted training sample payload."""
    model_config = ConfigDict(frozen=True)


class PlainTextPayload(SerializedPayload):
    """Payload format for standard causal pre-training / text classification."""
    text: str


class ChatMLMessage(BaseModel):
    """A single conversational message role and content pair."""
    model_config = ConfigDict(frozen=True)

    role: Literal["system", "user", "assistant"]
    content: str


class ChatMLCitation(BaseModel):
    """Traceability metadata for a conversational training sample."""
    model_config = ConfigDict(frozen=True)

    source_document: str
    chapter: Optional[str] = None
    heading: Optional[str] = None
    section: Optional[str] = None
    pages: List[int]
    segment_ids: List[str]


class ChatMLPayload(SerializedPayload):
    """Payload format for ChatML conversational instruction tuning."""
    messages: List[ChatMLMessage]
    citation: Optional[ChatMLCitation] = None


class SerializedSample(BaseModel):
    """A strongly typed serialized sample output wrapper."""
    model_config = ConfigDict(frozen=True)

    sample_id: str
    sequence_number: int
    payload: Union[PlainTextPayload, ChatMLPayload]

    @field_validator("sequence_number")
    @classmethod
    def sequence_number_must_be_positive(cls, v: int) -> int:
        """Ensures sequence number is positive and starts at 1."""
        if v < 1:
            raise ValueError("sequence_number must be >= 1.")
        return v

    @field_validator("sample_id")
    @classmethod
    def sample_id_must_be_valid_sha256(cls, v: str) -> str:
        """Ensures sample ID matches 64-character lowercase SHA256 hex format."""
        if not SHA256_HEX_PATTERN.match(v):
            raise ValueError("sample_id must be a valid 64-character lowercase SHA256 hex string.")
        return v


class SerializedDocument(BaseModel):
    """A collection of serialized samples for a single document."""
    model_config = ConfigDict(frozen=True)

    doc_id: str
    samples: List[SerializedSample]

    @field_validator("samples")
    @classmethod
    def samples_must_not_be_empty(cls, v: List[SerializedSample]) -> List[SerializedSample]:
        """Ensures serialized document contains at least one sample."""
        if not v:
            raise ValueError("samples list must not be empty.")
        return v


class SerializedCorpus(BaseModel):
    """A complete strongly typed serialized corpus."""
    model_config = ConfigDict(frozen=True)

    corpus_id: UUID
    documents: List[SerializedDocument]

    @field_validator("documents")
    @classmethod
    def documents_must_not_be_empty(cls, v: List[SerializedDocument]) -> List[SerializedDocument]:
        """Ensures serialized corpus contains at least one document."""
        if not v:
            raise ValueError("documents list must not be empty.")
        return v


class ExportResult(BaseModel):
    """Immutable report containing details of the file export outcomes."""
    model_config = ConfigDict(frozen=True)

    output_path: str
    format: ExportFormat
    documents_exported: int
    samples_exported: int
    bytes_written: int
    checksum: str
    export_timestamp: datetime
    export_duration: timedelta

    @field_validator("checksum")
    @classmethod
    def checksum_must_be_valid_sha256(cls, v: str) -> str:
        """Ensures checksum matches 64-character lowercase SHA256 hex format."""
        if not SHA256_HEX_PATTERN.match(v):
            raise ValueError("checksum must be a valid 64-character lowercase SHA256 hex string.")
        return v


class CorpusPipelineResult(BaseModel):
    """Immutable final report output from the CorpusPipeline execution."""
    model_config = ConfigDict(frozen=True)

    training_corpus: TrainingCorpus
    validation_result: CorpusValidationResult
    serialized_corpus: SerializedCorpus
    export_result: ExportResult


class TrainingInput(BaseModel):
    """Clean type-safe interface boundary input model for QLoRA Trainer."""
    model_config = ConfigDict(frozen=True)

    training_corpus: TrainingCorpus
    export_result: ExportResult
