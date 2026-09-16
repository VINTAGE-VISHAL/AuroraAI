"""Context carrying domain graph structures, template registries, and config options."""

from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field

from aurora.models import KnowledgeGraph, SemanticChunkCollection
from aurora.studio.templates import PromptTemplate


class DatasetGenerationContext(BaseModel):
    """Immutable context encapsulating input graph assets and configuration parameter states."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    graph: KnowledgeGraph
    chunks: SemanticChunkCollection
    template_registry: Dict[str, PromptTemplate] = Field(default_factory=dict)
    generation_config: Dict[str, Any] = Field(default_factory=dict)
    release_metadata: Dict[str, Any] = Field(default_factory=dict)
