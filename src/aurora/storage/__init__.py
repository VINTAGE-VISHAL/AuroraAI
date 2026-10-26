"""Storage layer interfaces and orchestration for vector indexes, databases, and artifacts."""

from aurora.storage.embedding_service import SentenceTransformerEmbeddingService

__all__ = [
    "SentenceTransformerEmbeddingService",
]

