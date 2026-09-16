"""Interfaces for the Concept Taxonomy pipeline steps."""

from abc import abstractmethod
from typing import List

from aurora.core.pipeline import IPipelineStep, PipelineContext
from aurora.models import Concept


class ITaxonomyStep(IPipelineStep[List[Concept], List[Concept]]):
    """Abstract contract for Concept Taxonomy processing and validation steps."""

    @abstractmethod
    def process(
        self, input_data: List[Concept], context: PipelineContext
    ) -> List[Concept]:
        """Applies taxonomy checks, cleanup, or indexing steps."""
        pass
