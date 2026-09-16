"""CorpusPipeline implementation coordinating builder, validator, serializer, and exporter."""

from typing import List, Optional

from aurora.config.settings import Settings
from aurora.core.exceptions import ConfigurationError
from aurora.core.logging import get_logger
from aurora.corpus.builder import LosslessCorpusBuilder
from aurora.corpus.exporter import JSONLExporter
from aurora.corpus.serializer import CorpusSerializer, PlainTextStrategy, ChatMLStrategy
from aurora.corpus.validator import CorpusValidator
from aurora.interfaces.corpus import (
    ICorpusExporter,
    ICorpusPipeline,
    ICorpusValidator,
    ILosslessCorpusBuilder,
    ITrainingSerializer,
)
from aurora.models.document import StructuredDocument
from aurora.models.training_corpus import CorpusPipelineResult
from aurora.registry.module_registry import ModuleRegistry

logger = get_logger("corpus")


@ModuleRegistry.register("corpus")
class CorpusPipeline(ICorpusPipeline):
    """Pipeline component for converting StructuredDocuments to a lossless training corpus."""

    def __init__(
        self,
        config: Settings,
        builder: Optional[ILosslessCorpusBuilder] = None,
        validator: Optional[ICorpusValidator] = None,
        serializer: Optional[ITrainingSerializer] = None,
        exporter: Optional[ICorpusExporter] = None,
    ) -> None:
        self.config = config
        self.builder = builder or LosslessCorpusBuilder()
        self.validator = validator or CorpusValidator()

        # Select serializer based on configuration
        if serializer is not None:
            self.serializer = serializer
        else:
            from aurora.corpus.serializer import InstructionStrategy, ExamStrategy, FlashcardStrategy
            ser_type = self.config.corpus.serializer_type.lower()
            if ser_type == "plain":
                self.serializer = CorpusSerializer(PlainTextStrategy())
            elif ser_type == "chatml":
                self.serializer = CorpusSerializer(ChatMLStrategy())
            elif ser_type == "instruction":
                self.serializer = CorpusSerializer(InstructionStrategy())
            elif ser_type == "exam":
                self.serializer = CorpusSerializer(ExamStrategy())
            elif ser_type == "flashcard":
                self.serializer = CorpusSerializer(FlashcardStrategy())
            else:
                raise ConfigurationError(
                    f"Unsupported serializer_type: '{self.config.corpus.serializer_type}'. Expected 'plain', 'chatml', 'instruction', 'exam', or 'flashcard'."
                )

        self.exporter = exporter or JSONLExporter()

    def run(self, input_data: List[StructuredDocument]) -> CorpusPipelineResult:
        """Runs building, validation, serialization, and file export in sequence."""
        logger.info("[Phase C] Building corpus...")
        corpus = self.builder.build(input_data)

        logger.info("[Phase C] Validating corpus...")
        val_result = self.validator.validate(corpus)

        logger.info("[Phase C] Serializing corpus...")
        serialized = self.serializer.serialize(corpus)

        logger.info("[Phase C] Exporting corpus...")
        exp_result = self.exporter.export(serialized, self.config.corpus.output_path)

        logger.info("[Phase C] Completed successfully.")

        return CorpusPipelineResult(
            training_corpus=corpus,
            validation_result=val_result,
            serialized_corpus=serialized,
            export_result=exp_result,
        )
