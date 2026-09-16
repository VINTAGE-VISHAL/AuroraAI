"""Interfaces and payload structures for the Semantic Chunk Builder pipeline."""

from abc import abstractmethod
from typing import List

from pydantic import BaseModel, ConfigDict, Field

from aurora.core.pipeline import IPipelineStep, PipelineContext
from aurora.models import KnowledgeGraph, SemanticChunk


class ChunkPayload(BaseModel):
    """Payload carrying state between Semantic Chunk builder steps."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    graph: KnowledgeGraph
    chunks: List[SemanticChunk] = Field(default_factory=list)


class IChunkStep(IPipelineStep[ChunkPayload, ChunkPayload]):
    """Abstract contract for steps in the Semantic Chunk Builder pipeline."""

    @abstractmethod
    def process(
        self, input_data: ChunkPayload, context: PipelineContext
    ) -> ChunkPayload:
        """Processes and enriches the chunk builder payload."""
        pass
