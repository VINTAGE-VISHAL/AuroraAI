"""Semantic retriever interface contract."""

from abc import ABC, abstractmethod
from typing import Optional

from aurora.models.retrieval import RetrievalResult


class ISemanticRetriever(ABC):
    """Behavioral contract for semantic query embedding and top-k chunk retrieval."""

    @abstractmethod
    def retrieve(
        self,
        query: str,
        conversation_id: str,
        top_k: Optional[int] = None,
        file_id: Optional[str] = None,
    ) -> RetrievalResult:
        """Retrieves top-k relevant document chunks for a query within a conversation scope.
        
        Args:
            query: User search text/query.
            conversation_id: Isolation boundary for conversation scope.
            top_k: Optional maximum number of chunks to return (defaults to configuration).
            file_id: Optional single file filter within conversation.
            
        Returns:
            RetrievalResult containing ranked ScoredChunks with scores, distances, and metadata.
        """
        pass
