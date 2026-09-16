"""Understanding / knowledge extraction layer contract."""

from abc import abstractmethod
from typing import List

from aurora.interfaces.base import IPipelineComponent
from aurora.models.curriculum import Curriculum
from aurora.models.document import ProcessedDocument


class ICurriculumExtractor(IPipelineComponent[List[ProcessedDocument], Curriculum]):
    """Contract for extracting domain curriculum structure and key concepts."""

    @abstractmethod
    def run(self, input_data: List[ProcessedDocument]) -> Curriculum:
        """Extracts structured curriculum knowledge from processed documents."""
        pass
