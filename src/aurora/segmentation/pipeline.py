"""Pipeline orchestrating sequential document structural segmentation steps."""

import hashlib
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from aurora.core.exceptions import InvalidSegmentError, SegmentationFailedError
from aurora.core.pipeline import BasePipeline, PipelineContext, PipelineResult
from aurora.models import (
    ArtifactMetadata,
    FrameworkInfo,
    NormalizedDocument,
    PipelineProvenance,
    SourceReference,
    StructuredDocument,
)
from aurora.models.enums import DocumentState, SegmentType
from aurora.models.segment import DocumentSegment
from aurora.segmentation.interfaces import ISegmentationStep


class TextbookHeaderSegmentationStep(ISegmentationStep):
    """Splits text blocks by Chapter titles, numbered section headers, and markdown headers."""

    def process(
        self, input_data: List[DocumentSegment], context: PipelineContext
    ) -> List[DocumentSegment]:
        output: List[DocumentSegment] = []
        # Matches: "Chapter 21", "C H A P T E R 21", "UNIT III", or "21.1 Overview", "21.1.1 parallel system", or markdown "# Introduction"
        pattern = re.compile(
            r"(?:^|\n)("
            r"(?:C\s*H\s*A\s*P\s*T\s*E\s*R\s+\d+|Chapter\s+\d+|UNIT\s+[IVXLCDM]+)(?:\s+[^\n]+)?"
            r"|"
            r"(\d+\.\d+(?:\.\d+)*)\s+([^\n]+)"
            r"|"
            r"(#{1,6})\s+([^\n]+)"
            r")(?=\n|$)",
            re.IGNORECASE
        )

        for seg in input_data:
            if seg.type != SegmentType.METADATA:
                output.append(seg)
                continue

            text = seg.text
            matches = list(pattern.finditer(text))
            if not matches:
                output.append(seg)
                continue

            last_idx = 0
            for match in matches:
                start, end = match.span()
                if text[start] == "\n":
                    start += 1

                # Capture text before heading as metadata
                if start > last_idx:
                    pre_text = text[last_idx:start]
                    output.append(
                        DocumentSegment(
                            segment_id="",
                            doc_id=seg.doc_id,
                            type=SegmentType.METADATA,
                            text=pre_text,
                            level=0,
                            start_offset=seg.start_offset + last_idx,
                            end_offset=seg.start_offset + start,
                            segment_index=0,
                            provenance=seg.provenance,
                        )
                    )

                # Determine heading type and level
                matched_text = text[start:end]
                lowered = matched_text.lower()
                
                # Check match groups
                groups = match.groups()
                # groups structure:
                # 0: full matched group text
                # 1: section numbering (e.g. 21.1)
                # 2: section title text (e.g. Overview)
                # 3: markdown hashes (e.g. ##)
                # 4: markdown title text (e.g. SubSection)

                if groups[3] is not None:
                    # Markdown heading
                    level = len(groups[3])
                elif "chapter" in lowered or "unit" in lowered:
                    # Chapter / Unit heading
                    level = 1
                elif groups[1] is not None:
                    # Numbered section
                    dots = groups[1].count(".")
                    level = dots + 1
                else:
                    level = 1

                output.append(
                    DocumentSegment(
                        segment_id="",
                        doc_id=seg.doc_id,
                        type=SegmentType.HEADING,
                        text=matched_text,
                        level=level,
                        start_offset=seg.start_offset + start,
                        end_offset=seg.start_offset + end,
                        segment_index=0,
                        provenance=seg.provenance,
                    )
                )
                last_idx = end

            # Capture remaining text trailing the last header
            if last_idx < len(text):
                post_text = text[last_idx:]
                output.append(
                    DocumentSegment(
                        segment_id="",
                        doc_id=seg.doc_id,
                        type=SegmentType.METADATA,
                        text=post_text,
                        level=0,
                        start_offset=seg.start_offset + last_idx,
                        end_offset=seg.start_offset + len(text),
                        segment_index=0,
                        provenance=seg.provenance,
                    )
                )

        return output


class HeaderSegmentationStep(ISegmentationStep):
    """Splits text blocks by Markdown headers, mapping heading levels."""

    def process(
        self, input_data: List[DocumentSegment], context: PipelineContext
    ) -> List[DocumentSegment]:
        output: List[DocumentSegment] = []
        heading_pattern = re.compile(r"(?:^|\n)(#{1,6})\s+(.+?)(?=\n|$)")

        for seg in input_data:
            if seg.type != SegmentType.METADATA:
                output.append(seg)
                continue

            text = seg.text
            matches = list(heading_pattern.finditer(text))
            if not matches:
                output.append(seg)
                continue

            last_idx = 0
            for match in matches:
                start, end = match.span()
                if text[start] == "\n":
                    start += 1

                # Capture text before heading as metadata (unsegmented placeholder)
                if start > last_idx:
                    pre_text = text[last_idx:start]
                    output.append(
                        DocumentSegment(
                            segment_id="",
                            doc_id=seg.doc_id,
                            type=SegmentType.METADATA,
                            text=pre_text,
                            level=0,
                            start_offset=seg.start_offset + last_idx,
                            end_offset=seg.start_offset + start,
                            segment_index=0,
                            provenance=seg.provenance,
                        )
                    )

                # Capture heading segment
                level = len(match.group(1))
                output.append(
                    DocumentSegment(
                        segment_id="",
                        doc_id=seg.doc_id,
                        type=SegmentType.HEADING,
                        text=text[start:end],
                        level=level,
                        start_offset=seg.start_offset + start,
                        end_offset=seg.start_offset + end,
                        segment_index=0,
                        provenance=seg.provenance,
                    )
                )
                last_idx = end

            # Capture remaining text trailing the last header
            if last_idx < len(text):
                post_text = text[last_idx:]
                output.append(
                    DocumentSegment(
                        segment_id="",
                        doc_id=seg.doc_id,
                        type=SegmentType.METADATA,
                        text=post_text,
                        level=0,
                        start_offset=seg.start_offset + last_idx,
                        end_offset=seg.start_offset + len(text),
                        segment_index=0,
                        provenance=seg.provenance,
                    )
                )

        return output


class CodeBlockSegmentationStep(ISegmentationStep):
    """Splits text blocks by Markdown code blocks."""

    def process(
        self, input_data: List[DocumentSegment], context: PipelineContext
    ) -> List[DocumentSegment]:
        output: List[DocumentSegment] = []
        code_pattern = re.compile(r"```[\s\S]*?```")

        for seg in input_data:
            if seg.type != SegmentType.METADATA:
                output.append(seg)
                continue

            text = seg.text
            matches = list(code_pattern.finditer(text))
            if not matches:
                output.append(seg)
                continue

            last_idx = 0
            for match in matches:
                start, end = match.span()
                # Capture text before code block
                if start > last_idx:
                    pre_text = text[last_idx:start]
                    output.append(
                        DocumentSegment(
                            segment_id="",
                            doc_id=seg.doc_id,
                            type=SegmentType.METADATA,
                            text=pre_text,
                            level=0,
                            start_offset=seg.start_offset + last_idx,
                            end_offset=seg.start_offset + start,
                            segment_index=0,
                            provenance=seg.provenance,
                        )
                    )

                # Capture code block segment
                output.append(
                    DocumentSegment(
                        segment_id="",
                        doc_id=seg.doc_id,
                        type=SegmentType.CODE_BLOCK,
                        text=text[start:end],
                        level=0,
                        start_offset=seg.start_offset + start,
                        end_offset=seg.start_offset + end,
                        segment_index=0,
                        provenance=seg.provenance,
                    )
                )
                last_idx = end

            # Capture remaining text trailing the last code block
            if last_idx < len(text):
                post_text = text[last_idx:]
                output.append(
                    DocumentSegment(
                        segment_id="",
                        doc_id=seg.doc_id,
                        type=SegmentType.METADATA,
                        text=post_text,
                        level=0,
                        start_offset=seg.start_offset + last_idx,
                        end_offset=seg.start_offset + len(text),
                        segment_index=0,
                        provenance=seg.provenance,
                    )
                )

        return output


class ParagraphSegmentationStep(ISegmentationStep):
    """Refines remaining METADATA blocks into Paragraph segments divided by double newlines, preserving all characters."""

    def process(
        self, input_data: List[DocumentSegment], context: PipelineContext
    ) -> List[DocumentSegment]:
        output: List[DocumentSegment] = []

        for seg in input_data:
            if seg.type != SegmentType.METADATA:
                output.append(seg)
                continue

            text = seg.text
            if not text:
                continue

            # Split by double newlines but retain the separators as part of the paragraph segments
            parts = text.split("\n\n")
            last_idx = 0

            for i, part in enumerate(parts):
                suffix = "\n\n" if i < len(parts) - 1 else ""
                full_part = part + suffix
                if not full_part:
                    continue

                start = last_idx
                end = start + len(full_part)

                if not part.strip():
                    # If we already have segments in output, append this whitespace to the last segment
                    if output:
                        prev = output[-1]
                        updated = prev.model_copy(update={
                            "text": prev.text + full_part,
                            "end_offset": prev.end_offset + len(full_part)
                        })
                        output[-1] = updated
                    else:
                        # Fallback: create a segment if there is no previous segment
                        output.append(
                            DocumentSegment(
                                segment_id="",
                                doc_id=seg.doc_id,
                                type=SegmentType.PARAGRAPH,
                                text=full_part,
                                level=0,
                                start_offset=seg.start_offset + start,
                                end_offset=seg.start_offset + end,
                                segment_index=0,
                                provenance=seg.provenance,
                            )
                        )
                else:
                    output.append(
                        DocumentSegment(
                            segment_id="",
                            doc_id=seg.doc_id,
                            type=SegmentType.PARAGRAPH,
                            text=full_part,
                            level=0,
                            start_offset=seg.start_offset + start,
                            end_offset=seg.start_offset + end,
                            segment_index=0,
                            provenance=seg.provenance,
                        )
                    )
                last_idx = end

        return output


class _TempSegment:
    """Temporary mutable class for building parent-child relationships."""

    def __init__(
        self,
        segment_id: str,
        doc_id: str,
        type_: SegmentType,
        text: str,
        level: int,
        start_offset: int,
        end_offset: int,
        segment_index: int,
        provenance: PipelineProvenance,
    ) -> None:
        self.segment_id = segment_id
        self.doc_id = doc_id
        self.type = type_
        self.text = text
        self.level = level
        self.start_offset = start_offset
        self.end_offset = end_offset
        self.segment_index = segment_index
        self.provenance = provenance
        self.parent_id: Optional[str] = None


class SegmentationPipeline(BasePipeline[NormalizedDocument, StructuredDocument]):
    """Pipeline coordinating sequential structural segmentation step transformations."""

    def __init__(self, steps: Optional[List[ISegmentationStep]] = None) -> None:
        if steps is None:
            # Default sequence: TextbookHeading -> CodeBlock -> Paragraph
            default_steps: List[ISegmentationStep] = [
                TextbookHeaderSegmentationStep(),
                CodeBlockSegmentationStep(),
                ParagraphSegmentationStep(),
            ]
            super().__init__(default_steps)  # type: ignore
        else:
            super().__init__(steps)  # type: ignore

    def _build_segments(
        self, current_segments: List[DocumentSegment], source_uri: str
    ) -> List[DocumentSegment]:
        """Compile IDs and hierarchy relations using mutable structures."""
        temp_list: List[_TempSegment] = []
        active_headings: List[Tuple[int, int]] = []  # stack of (level, temp_idx)
        children_map: Dict[int, List[str]] = {}     # temp_idx -> List[str] (IDs)
        parent_map: Dict[int, Optional[int]] = {}       # temp_idx -> Optional[str] (ID)

        # 1st Pass: Compute stable hashes and mapping relations
        for idx, seg in enumerate(current_segments):
            # Compute stable ID: SHA256(doc_id:type:start_offset:end_offset)
            hash_input = f"{seg.doc_id}:{seg.type}:{seg.start_offset}:{seg.end_offset}"
            seg_id = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

            temp_list.append(
                _TempSegment(
                    segment_id=seg_id,
                    doc_id=seg.doc_id,
                    type_=seg.type,
                    text=seg.text,
                    level=seg.level,
                    start_offset=seg.start_offset,
                    end_offset=seg.end_offset,
                    segment_index=idx,
                    provenance=seg.provenance,
                )
            )
            children_map[idx] = []
            parent_map[idx] = None

            if seg.type == SegmentType.HEADING:
                while active_headings and active_headings[-1][0] >= seg.level:
                    active_headings.pop()
                if active_headings:
                    parent_idx = active_headings[-1][1]
                    parent_map[idx] = parent_idx
                active_headings.append((seg.level, idx))
            else:
                if active_headings:
                    parent_idx = active_headings[-1][1]
                    parent_map[idx] = parent_idx

        # 2nd Pass: Populate children lists
        for child_idx, p_idx in parent_map.items():
            if p_idx is not None:
                parent_id = temp_list[p_idx].segment_id
                child_id = temp_list[child_idx].segment_id
                temp_list[child_idx].parent_id = parent_id
                children_map[p_idx].append(child_id)

        # 3rd Pass: Construct Pydantic DocumentSegment models
        final_segments = []
        for idx, data in enumerate(temp_list):
            source_ref = SourceReference(
                source_uri=source_uri,
                page_number=None,
                start_offset=data.start_offset,
                end_offset=data.end_offset,
                segment_id=data.segment_id,
            )
            final_segments.append(
                DocumentSegment(
                    segment_id=data.segment_id,
                    doc_id=data.doc_id,
                    type=data.type,
                    text=data.text,
                    level=data.level,
                    parent_id=data.parent_id,
                    children_ids=children_map[idx],
                    start_offset=data.start_offset,
                    end_offset=data.end_offset,
                    segment_index=data.segment_index,
                    provenance=data.provenance,
                    source_reference=source_ref,
                )
            )
        return final_segments

    def _validate_segments(self, final_segments: List[DocumentSegment], text: str) -> None:
        """Validate offsets alignment and complete logical coverage."""
        last_offset = -1
        for seg in final_segments:
            if seg.start_offset < last_offset:
                raise InvalidSegmentError(
                    f"Overlapping segment offsets discovered at index {seg.segment_index}"
                )
            last_offset = seg.end_offset

            expected_text = text[seg.start_offset : seg.end_offset]
            if seg.text != expected_text:
                raise InvalidSegmentError(
                    f"Segment text mismatch for index {seg.segment_index}. "
                    f"Expected {repr(expected_text)}, got {repr(seg.text)}"
                )

        # Strict invariant assertion: reconstructed_text == original_text
        reconstructed = "".join(seg.text for seg in sorted(final_segments, key=lambda s: s.start_offset))
        if reconstructed != text:
            raise InvalidSegmentError(
                "Lossless reconstruction invariant violated! Reconstructed text does not match original."
            )

    def execute(
        self, input_data: NormalizedDocument, context: PipelineContext
    ) -> PipelineResult[StructuredDocument]:
        """Perform structural segmentation on NormalizedDocument."""
        import uuid
        if not input_data.text.strip():
            # Handle empty document case cleanly
            framework = FrameworkInfo(module_name="SegmentationPipeline", module_version="0.1.0")
            provenance = PipelineProvenance(
                stage=DocumentState.SEGMENTED,
                producer="SegmentationPipeline",
                timestamp=datetime.now(timezone.utc),
                framework=framework,
                run_id=input_data.provenance.run_id,
                execution_id=input_data.provenance.execution_id,
            )
            artifact = ArtifactMetadata(
                artifact_id=uuid.uuid4(),
                parent_artifact_ids=[input_data.artifact.artifact_id],
                derived_from=[input_data.artifact.artifact_id],
                checksum=hashlib.sha256(b"").hexdigest(),
                created_at=provenance.timestamp,
                schema_version="1.0.0",
            )
            result_doc = StructuredDocument(
                doc_id=input_data.doc_id,
                segments=[],
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

        # Wrap raw text into one starting METADATA segment (unsegmented placeholder type)
        initial_segment = DocumentSegment(
            segment_id="",
            doc_id=input_data.doc_id,
            type=SegmentType.METADATA,
            text=input_data.text,
            level=0,
            start_offset=0,
            end_offset=len(input_data.text),
            segment_index=0,
            provenance=input_data.provenance,
        )

        current_segments = [initial_segment]
        try:
            for step in self.steps:
                current_segments = step.process(current_segments, context)
        except Exception as e:
            raise SegmentationFailedError(f"Segmentation failed: {e}") from e

        final_segments = self._build_segments(current_segments, input_data.metadata.source_path)
        self._validate_segments(final_segments, input_data.text)

        framework = FrameworkInfo(module_name="SegmentationPipeline", module_version="0.1.0")
        provenance = PipelineProvenance(
            stage=DocumentState.SEGMENTED,
            producer="SegmentationPipeline",
            timestamp=datetime.now(timezone.utc),
            framework=framework,
            run_id=input_data.provenance.run_id,
            execution_id=input_data.provenance.execution_id,
        )

        content_hash = hashlib.sha256(
            "".join(s.segment_id for s in final_segments).encode("utf-8")
        ).hexdigest()
        artifact = ArtifactMetadata(
            artifact_id=uuid.uuid4(),
            parent_artifact_ids=[input_data.artifact.artifact_id],
            derived_from=[input_data.artifact.artifact_id],
            checksum=content_hash,
            created_at=provenance.timestamp,
            schema_version="1.0.0",
        )

        result_doc = StructuredDocument(
            doc_id=input_data.doc_id,
            segments=final_segments,
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
