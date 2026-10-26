"""Context fusion and prompt assembly interface contracts."""

from abc import ABC, abstractmethod
from typing import List, Optional

from aurora.models.context_fusion import FusedContext, GroundedPrompt
from aurora.models.retrieval import ScoredChunk


class IContextFusionService(ABC):
    """Behavioral contract for fusing retrieved chunks into a budget-bounded, structured RAG context."""

    @abstractmethod
    def fuse_context(
        self,
        query: str,
        chunks: List[ScoredChunk],
        conversation_id: str,
        max_tokens: Optional[int] = None,
    ) -> FusedContext:
        """Assembles and deduplicates retrieved chunks within a strict token budget.
        
        Args:
            query: The user query.
            chunks: Ordered sequence of ScoredChunks (ranked descending by relevance).
            conversation_id: Conversation isolation scope.
            max_tokens: Optional maximum token budget (overrides default configuration).
            
        Returns:
            FusedContext containing the formatted context text and rich source metadata.
        """
        pass

    @abstractmethod
    def assemble_grounded_prompt(
        self,
        query: str,
        fused_context: FusedContext,
        base_system_prompt: Optional[str] = None,
    ) -> GroundedPrompt:
        """Constructs a grounded LLM prompt separating trusted instructions from untrusted document context."""
        pass
