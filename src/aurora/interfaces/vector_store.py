"""Vector store interface contract."""

from abc import ABC, abstractmethod
from typing import List, Optional

from aurora.models.embedding import EmbeddedChunk
from aurora.models.retrieval import ScoredChunk
from aurora.models.vector_store import VectorRecord


class IVectorStore(ABC):
    """Behavioral contract for persistent runtime vector indexing, retrieval prep, and lifecycle operations."""

    @abstractmethod
    def store_embedded_chunks(
        self,
        conversation_id: str,
        chunks: List[EmbeddedChunk],
    ) -> int:
        """Stores or upserts a batch of EmbeddedChunks into the conversation's vector collection.
        
        Args:
            conversation_id: Conversation isolation scope identifier.
            chunks: List of EmbeddedChunks to store.
            
        Returns:
            Number of vectors successfully indexed.
        """
        pass

    @abstractmethod
    def get_chunk(
        self,
        conversation_id: str,
        chunk_id: str,
    ) -> Optional[VectorRecord]:
        """Retrieves a single stored vector record by chunk_id within a conversation scope."""
        pass

    @abstractmethod
    def get_file_chunks(
        self,
        conversation_id: str,
        file_id: str,
    ) -> List[VectorRecord]:
        """Retrieves all vector records belonging to a file within a conversation scope."""
        pass

    @abstractmethod
    def count(self, conversation_id: str, file_id: Optional[str] = None) -> int:
        """Returns the total number of vectors in a conversation, optionally filtered by file_id."""
        pass

    @abstractmethod
    def delete_file(
        self,
        conversation_id: str,
        file_id: str,
    ) -> int:
        """Deletes all vectors associated with a file within a conversation scope.
        
        Returns:
            Number of vectors deleted (or 0 if none existed).
        """
        pass

    @abstractmethod
    def delete_conversation(
        self,
        conversation_id: str,
    ) -> bool:
        """Deletes the entire vector collection for a conversation."""
        pass

    @abstractmethod
    def query_vectors(
        self,
        conversation_id: str,
        query_vector: List[float],
        top_k: int = 5,
        file_id: Optional[str] = None,
    ) -> List[ScoredChunk]:
        """Queries the conversation's vector collection for the most similar chunks.
        
        Args:
            conversation_id: Conversation isolation scope identifier.
            query_vector: Dense query embedding vector.
            top_k: Maximum number of nearest neighbors to return.
            file_id: Optional file filter within the conversation.
            
        Returns:
            Ranked list of ScoredChunks sorted by relevance score descending.
        """
        pass
