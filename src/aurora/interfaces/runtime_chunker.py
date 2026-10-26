"""Runtime document preprocessing and text chunking interfaces."""

from abc import ABC, abstractmethod
from typing import Optional

from aurora.models.file_metadata import ExtractedFileResponse
from aurora.models.runtime_chunk import ChunkingConfig, ChunkingResult


class IRuntimeChunker(ABC):
    """Behavioral contract for document cleaning and overlapping text chunking."""

    @abstractmethod
    def chunk_extracted_document(
        self,
        extracted: ExtractedFileResponse,
        config: Optional[ChunkingConfig] = None,
    ) -> ChunkingResult:
        """Processes extracted document text into overlapping, attribution-preserving DocumentChunks."""
        pass
