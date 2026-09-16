"""Pipeline orchestrating sequential document normalization steps."""

import re
import unicodedata
from datetime import datetime, timezone
from typing import List, Optional

from aurora.core.exceptions import InvalidNormalizationError, NormalizationFailedError
from aurora.core.pipeline import BasePipeline, PipelineContext, PipelineResult
from aurora.extraction.models import ExtractedDocument
from aurora.models import FrameworkInfo, NormalizedDocument, PipelineProvenance
from aurora.models.enums import DocumentState
from aurora.normalization.interfaces import INormalizationStep
from aurora.normalization.models import NormalizationContext


class LineEndingNormalizer(INormalizationStep):
    """Standardises line breaks to Unix style newlines (LF)."""

    def process(self, input_data: str, context: PipelineContext) -> str:
        return input_data.replace("\r\n", "\n").replace("\r", "\n")


class ControlCharacterNormalizer(INormalizationStep):
    """Removes non-printable ASCII control characters (keeping tab and newlines)."""

    def process(self, input_data: str, context: PipelineContext) -> str:
        ctx = context if isinstance(context, NormalizationContext) else NormalizationContext()
        if not ctx.remove_control_characters:
            return input_data
        # Match ASCII control characters except tab (0x09) and newline (0x0a)
        control_chars = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
        return control_chars.sub("", input_data)


class UnicodeNormalizer(INormalizationStep):
    """Applies canonical Unicode Normalization Form C (NFC)."""

    def process(self, input_data: str, context: PipelineContext) -> str:
        ctx = context if isinstance(context, NormalizationContext) else NormalizationContext()
        if not ctx.normalize_unicode:
            return input_data
        return unicodedata.normalize("NFC", input_data)


class WhitespaceNormalizer(INormalizationStep):
    """Collapses duplicate inline spaces while preserving code block indentations."""

    def process(self, input_data: str, context: PipelineContext) -> str:
        ctx = context if isinstance(context, NormalizationContext) else NormalizationContext()
        if not ctx.collapse_whitespace:
            return input_data

        lines = input_data.split("\n")
        in_code_block = False
        cleaned_lines = []

        for line in lines:
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                cleaned_lines.append(line)
                continue

            if in_code_block and ctx.preserve_code_blocks:
                cleaned_lines.append(line)
            else:
                # Collapse repeated spaces, but don't strip leading tabs/spaces completely
                stripped = line.strip()
                if not stripped:
                    cleaned_lines.append("")
                else:
                    # Collapse multiple spaces to a single space
                    collapsed = re.sub(r"[ \t]+", " ", line)
                    cleaned_lines.append(collapsed)

        return "\n".join(cleaned_lines)


class NormalizationPipeline(BasePipeline[ExtractedDocument, NormalizedDocument]):
    """Coordinates ordered execution of text normalization steps."""

    def __init__(self, steps: Optional[List[INormalizationStep]] = None) -> None:
        if steps is None:
            # Default sequence: LineEndings -> ControlChars -> Unicode -> Whitespace
            default_steps: List[INormalizationStep] = [
                LineEndingNormalizer(),
                ControlCharacterNormalizer(),
                UnicodeNormalizer(),
                WhitespaceNormalizer(),
            ]
            super().__init__(default_steps)  # type: ignore
        else:
            super().__init__(steps)  # type: ignore

    def normalize(
        self, doc: ExtractedDocument, context: Optional[NormalizationContext] = None
    ) -> NormalizedDocument:
        """Helper to run normalizer directly (compatibility wrapper)."""
        ctx = context or NormalizationContext()
        return self.execute(doc, ctx).result

    def execute(
        self, input_data: ExtractedDocument, context: PipelineContext
    ) -> PipelineResult[NormalizedDocument]:
        """Run extracted text through pipeline steps and return PipelineResult."""
        if not isinstance(context, NormalizationContext):
            raise InvalidNormalizationError(
                "PipelineContext must be NormalizationContext subclass."
            )

        current_text = input_data.text

        try:
            for step in self.steps:
                current_text = step.process(current_text, context)
        except Exception as e:
            raise NormalizationFailedError(f"Normalization step failed: {e}") from e

        # Update operational metrics
        context.metrics["original_length"] = len(input_data.text)
        context.metrics["normalized_length"] = len(current_text)

        framework = FrameworkInfo(
            module_name="NormalizationPipeline",
            module_version="0.1.0",
        )
        provenance = PipelineProvenance(
            stage=DocumentState.NORMALIZED,
            producer="NormalizationPipeline",
            timestamp=datetime.now(timezone.utc),
            framework=framework,
            run_id=input_data.provenance.run_id,
            execution_id=input_data.provenance.execution_id,
        )

        import hashlib
        import uuid

        from aurora.models import ArtifactMetadata

        content_hash = hashlib.sha256(current_text.encode("utf-8")).hexdigest()
        artifact = ArtifactMetadata(
            artifact_id=uuid.uuid4(),
            parent_artifact_ids=[input_data.artifact.artifact_id],
            derived_from=[input_data.artifact.artifact_id],
            checksum=content_hash,
            created_at=provenance.timestamp,
            schema_version="1.0.0",
        )

        result_doc = NormalizedDocument(
            doc_id=input_data.doc_id,
            text=current_text,
            tables=list(input_data.tables),
            images=list(input_data.images),
            links=list(input_data.links),
            metadata=input_data.metadata,
            provenance=provenance,
            artifact=artifact,
        )

        return PipelineResult(
            result=result_doc,
            metrics=context.metrics,
            warnings=context.warnings,
            diagnostics=context.diagnostics,
        )
