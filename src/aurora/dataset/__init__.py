"""Dataset engineering phase package."""

from aurora.config.settings import Settings
from aurora.interfaces.dataset import IDatasetGenerator
from aurora.models.curriculum import Curriculum
from aurora.models.dataset import InstructionDataset, QAPair
from aurora.registry.module_registry import ModuleRegistry


@ModuleRegistry.register("dataset")
class DefaultDatasetGenerator(IDatasetGenerator):
    """Default instruction tuning dataset generator implementation."""

    def __init__(self, config: Settings) -> None:
        self.config = config

    def run(self, input_data: Curriculum) -> InstructionDataset:
        pairs = []
        for concept in input_data.concepts:
            pairs.append(
                QAPair(
                    instruction=f"What is {concept.name}?",
                    response=f"It is defined as: {concept.description}",
                    reference_concept=concept.name,
                )
            )
        return InstructionDataset(
            name=f"{input_data.domain} Dataset",
            pairs=pairs,
            split="train",
        )
