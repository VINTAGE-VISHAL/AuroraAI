"""Contracts and protocols for dataset generators and plugins."""

from typing import List, Protocol

from pydantic import BaseModel, ConfigDict

from aurora.models import DatasetCollection
from aurora.studio.context import DatasetGenerationContext


class GeneratorDescriptor(BaseModel):
    """Immutable metadata descriptor defining properties of a generator plugin."""
    model_config = ConfigDict(frozen=True)

    name: str
    version: str
    supported_formats: List[str]
    template_version: str


class IDatasetGenerator(Protocol):
    """Protocol for pluggable dataset format compilers."""

    @property
    def descriptor(self) -> GeneratorDescriptor:
        """Exposes the plugin registration descriptor metadata."""
        ...

    def generate(self, context: DatasetGenerationContext) -> DatasetCollection:
        """Processes semantic chunks into training DatasetCollection."""
        ...
