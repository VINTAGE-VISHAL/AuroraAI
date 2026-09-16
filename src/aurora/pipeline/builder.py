"""Builder for compiling components into a pipeline."""

from typing import List

from aurora.config.settings import Settings
from aurora.interfaces.base import IPipelineComponent
from aurora.pipeline.pipeline import Pipeline
from aurora.registry.module_registry import ModuleRegistry


class PipelineBuilder:
    """Builder class to construct a Pipeline execution flow."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.components: List[IPipelineComponent] = []

    def add_component(self, name: str) -> "PipelineBuilder":
        """Add a component by registry name."""
        component_cls = ModuleRegistry.get(name)
        self.components.append(component_cls(self.settings))
        return self

    def build(self) -> Pipeline:
        """Build the structured Pipeline."""
        return Pipeline(self.components)
