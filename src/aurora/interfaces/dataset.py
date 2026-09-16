"""Dataset engineering layer contract."""

from abc import abstractmethod

from aurora.interfaces.base import IPipelineComponent
from aurora.models.curriculum import Curriculum
from aurora.models.dataset import InstructionDataset


class IDatasetGenerator(IPipelineComponent[Curriculum, InstructionDataset]):
    """Contract for generating instruction-tuning QA pairs based on a curriculum."""

    @abstractmethod
    def run(self, input_data: Curriculum) -> InstructionDataset:
        """Generates instruction-tuning datasets from curriculum models."""
        pass
