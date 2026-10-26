"""Embedding service interface contract."""

from abc import ABC, abstractmethod
from typing import List

from aurora.models.embedding import EmbeddedChunk, EmbeddingBatchResult
from aurora.models.runtime_chunk import DocumentChunk


class IEmbeddingService(ABC):
    """Behavioral contract for runtime dense vector embedding generation."""

    @abstractmethod
    def embed_chunks(self, chunks: List[DocumentChunk]) -> EmbeddingBatchResult:
        """Generates dense vector embeddings for an ordered sequence of DocumentChunks."""
        pass

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generates a dense vector embedding for a single text query or string."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Returns the vector dimensionality produced by this embedding service."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Returns the canonical model identifier used for embedding generation."""
        pass
