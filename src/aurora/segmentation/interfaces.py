"""Interfaces for structural document segmentation steps."""

from abc import abstractmethod
from typing import List

from aurora.core.pipeline import IPipelineStep, PipelineContext
from aurora.models.segment import DocumentSegment


class ISegmentationStep(IPipelineStep[List[DocumentSegment], List[DocumentSegment]]):
    """Behavioral contract for text structural segmentation pipeline steps."""

    @abstractmethod
    def process(
        self, input_data: List[DocumentSegment], context: PipelineContext
    ) -> List[DocumentSegment]:
        """Processes current segment tree, refining UNKNOWN segments into concrete types."""
        pass
