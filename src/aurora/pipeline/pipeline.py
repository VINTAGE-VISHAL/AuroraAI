"""Base Pipeline execution class."""

from typing import Any, List

from aurora.interfaces.base import IPipelineComponent


class Pipeline:
    """Orchestrates sequential execution of pipeline components."""

    def __init__(self, components: List[IPipelineComponent]) -> None:
        self.components = components

    def execute(self, initial_input: Any) -> Any:

        """Run each component in sequence passing outputs as next inputs."""
        current_data = initial_input
        for component in self.components:
            current_data = component.run(current_data)
        return current_data
