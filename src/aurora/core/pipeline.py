"""Generic Pipeline Abstraction modeling unified step executions."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class PipelineContext:
    """Carries execution state, runtime metrics, configurations, and diagnostics."""

    def __init__(
        self,
        configuration: Optional[Dict[str, Any]] = None,
        run_id: Optional[UUID] = None,
        execution_id: Optional[UUID] = None,
    ) -> None:
        self.configuration: Dict[str, Any] = configuration or {}
        self.metrics: Dict[str, Any] = {}
        self.warnings: List[str] = []
        self.diagnostics: Dict[str, Any] = {}
        self.run_id: Optional[UUID] = run_id
        self.execution_id: Optional[UUID] = execution_id


class PipelineResult(BaseModel, Generic[OutputT]):
    """Standardized output wrapper for all pipeline executors."""
    model_config = ConfigDict(frozen=True)

    result: OutputT
    metrics: Dict[str, Any]
    warnings: List[str]
    diagnostics: Dict[str, Any]


class IPipelineStep(ABC, Generic[InputT, OutputT]):
    """Abstract behavioral contract for modular pipeline steps."""

    @abstractmethod
    def process(self, input_data: InputT, context: PipelineContext) -> OutputT:
        """Process input data and return step-specific result type."""
        pass


class BasePipeline(ABC, Generic[InputT, OutputT]):
    """Orchestrator base class executing structural step transformations."""

    def __init__(self, steps: List[IPipelineStep[Any, Any]]) -> None:
        self.steps = steps

    @abstractmethod
    def execute(self, input_data: InputT, context: PipelineContext) -> PipelineResult[OutputT]:
        """Execute the pipeline steps on the input data."""
        pass
