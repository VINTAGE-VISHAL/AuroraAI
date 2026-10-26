"""Runtime Semantic Retriever and Top-K Ranking Service.

Implements Module 06 requirements:
- Embeds search queries using the existing IEmbeddingService (no duplicate models)
- Queries the IVectorStore for conversation-scoped vector collections
- Enforces strict conversation isolation and optional file_id filtering
- Interprets cosine distance d correctly into similarity score s = 1.0 - d
- Ranks results descending by relevance score (with deterministic secondary sort)
- Preserves full DocumentChunk metadata, source_page numbers, and character offsets
- Gracefully handles empty queries, empty indexes, and non-existent collections
"""

import logging
from typing import Optional

from aurora.config.settings import RetrieverConfig
from aurora.core.exceptions import InvalidTopKError, RetrievalError
from aurora.interfaces.embedding import IEmbeddingService
from aurora.interfaces.retriever import ISemanticRetriever
from aurora.interfaces.vector_store import IVectorStore
from aurora.models.retrieval import RetrievalResult, ScoredChunk
from aurora.storage.embedding_service import SentenceTransformerEmbeddingService
from aurora.storage.vector_store import ChromaVectorStore

logger = logging.getLogger(__name__)


class SemanticRetriever(ISemanticRetriever):
    """Production semantic retriever that coordinates embedding generation and vector search."""

    def __init__(
        self,
        embedding_service: Optional[IEmbeddingService] = None,
        vector_store: Optional[IVectorStore] = None,
        config: Optional[RetrieverConfig] = None,
    ) -> None:
        self.embedding_service = embedding_service or SentenceTransformerEmbeddingService()
        self.vector_store = vector_store or ChromaVectorStore()
        self.config = config or RetrieverConfig()

    def retrieve(
        self,
        query: str,
        conversation_id: str,
        top_k: Optional[int] = None,
        file_id: Optional[str] = None,
    ) -> RetrievalResult:
        """Retrieves top-k relevant document chunks for a query within a conversation scope."""
        if not conversation_id or not conversation_id.strip():
            raise RetrievalError("conversation_id cannot be empty.")

        # Determine effective top_k
        effective_top_k = top_k if top_k is not None else self.config.default_top_k
        if not isinstance(effective_top_k, int) or effective_top_k <= 0:
            raise InvalidTopKError(f"top_k must be a positive integer, got: {effective_top_k}")

        if effective_top_k > self.config.max_top_k:
            effective_top_k = self.config.max_top_k

        # Clean/normalize query text
        clean_query = query.strip() if query else ""
        if not clean_query:
            return RetrievalResult(
                query=query,
                conversation_id=conversation_id,
                file_id=file_id,
                top_k=effective_top_k,
                total_retrieved=0,
                results=[],
            )

        # 1. Embed query using existing embedding service
        try:
            query_vector = self.embedding_service.embed_text(clean_query)
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            raise RetrievalError(f"Query embedding generation failed: {e}") from e

        # 2. Query vector store within conversation isolation scope
        try:
            scored_chunks = self.vector_store.query_vectors(
                conversation_id=conversation_id,
                query_vector=query_vector,
                top_k=effective_top_k,
                file_id=file_id,
            )
        except Exception as e:
            logger.error(f"Vector search failed for conversation '{conversation_id}': {e}")
            raise RetrievalError(f"Vector retrieval failed: {e}") from e

        # 3. Optional score threshold filtering if configured
        if self.config.min_score_threshold > 0.0:
            scored_chunks = [sc for sc in scored_chunks if sc.score >= self.config.min_score_threshold]

        return RetrievalResult(
            query=clean_query,
            conversation_id=conversation_id,
            file_id=file_id,
            top_k=effective_top_k,
            total_retrieved=len(scored_chunks),
            results=scored_chunks,
        )
