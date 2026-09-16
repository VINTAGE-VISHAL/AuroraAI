"""Understanding and curriculum extraction phase package."""

from typing import List

from aurora.config.settings import Settings
from aurora.interfaces.understanding import ICurriculumExtractor
from aurora.models.concept import Concept
from aurora.models.curriculum import Curriculum
from aurora.models.document import ProcessedDocument
from aurora.registry.module_registry import ModuleRegistry


@ModuleRegistry.register("understanding")
class DefaultCurriculumExtractor(ICurriculumExtractor):
    """Default curriculum and concept extraction implementation."""

    def __init__(self, config: Settings) -> None:
        self.config = config

    def run(self, input_data: List[ProcessedDocument]) -> Curriculum:
        concepts = [
            Concept(
                name="AI Foundation",
                description="Core artificial intelligence principles.",
                difficulty="beginner",
                prerequisites=[],
                reference_chunk_ids=[doc.doc_id for doc in input_data],
            )
        ]
        return Curriculum(
            domain="Educational AI",
            concepts=concepts,
            version="1.0.0",
        )
