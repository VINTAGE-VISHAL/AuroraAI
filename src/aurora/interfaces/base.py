"""Base interface definition for AuroraEngine pipeline modules."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from aurora.config.settings import Settings

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class IPipelineComponent(ABC, Generic[InputT, OutputT]):
    """Abstract interface contract for a pipeline component."""

    @abstractmethod
    def __init__(self, config: Settings) -> None:
        """Initialize the component with configuration settings."""
        pass

    @abstractmethod
    def run(self, input_data: InputT) -> OutputT:
        """Execute the component logic on the input data."""
        pass
