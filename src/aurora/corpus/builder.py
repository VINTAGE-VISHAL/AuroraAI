"""LosslessCorpusBuilder implementation for Phase C."""

import hashlib
import uuid
from typing import List, Optional

from aurora.core.artifact import ArtifactMetadata
from aurora.interfaces.corpus import ILosslessCorpusBuilder
from aurora.models.document import StructuredDocument
from aurora.models.enums import SegmentType
from aurora.models.segment import DocumentSegment
from aurora.models.training_corpus import (
    TrainingCorpus,
    TrainingDocument,
    TrainingSample,
    TrainingSampleMetadata,
    TrainingSampleTraceability,
)

# Seed namespace UUID for generating deterministic UUIDs
AURORA_NAMESPACE = uuid.UUID("d3b07ef3-6dda-4669-b34b-760a1743924e")


class LosslessCorpusBuilder(ILosslessCorpusBuilder):
    """Converts StructuredDocuments into a TrainingCorpus losslessly."""

    def build(self, documents: List[StructuredDocument]) -> TrainingCorpus:
        """Converts structured documents to a domain-specific TrainingCorpus."""
        if not documents:
            raise ValueError("documents list must not be empty.")

        training_docs: List[TrainingDocument] = []
        doc_artifact_ids: List[uuid.UUID] = []

        for s_doc in documents:
            t_doc = self._build_document(s_doc)
            training_docs.append(t_doc)
            doc_artifact_ids.append(s_doc.artifact.artifact_id)

        # Generate deterministic corpus artifact ID and UUID from hierarchical checksums
        corpus_payload = ":".join(doc.artifact.checksum for doc in training_docs)
        corpus_checksum = hashlib.sha256(corpus_payload.encode("utf-8")).hexdigest()
        corpus_uuid = uuid.uuid5(AURORA_NAMESPACE, f"corpus:{corpus_checksum}")
        corpus_artifact_id = uuid.uuid5(AURORA_NAMESPACE, f"corpus_artifact:{corpus_checksum}")

        # Deterministically derive creation timestamp from the latest parent document creation time
        latest_timestamp = max(doc.artifact.created_at for doc in training_docs)

        corpus_artifact = ArtifactMetadata(
            artifact_id=corpus_artifact_id,
            parent_artifact_ids=doc_artifact_ids,
            derived_from=doc_artifact_ids,
            checksum=corpus_checksum,
            created_at=latest_timestamp,
            schema_version="1.0.0",
        )

        return TrainingCorpus(
            corpus_id=corpus_uuid,
            documents=training_docs,
            artifact=corpus_artifact,
        )

    def _build_document(self, s_doc: StructuredDocument) -> TrainingDocument:
        """Builds a single TrainingDocument from a StructuredDocument."""
        if not s_doc.segments:
            raise ValueError("StructuredDocument has zero segments.")

        sections = self._group_sections(s_doc.segments)
        samples: List[TrainingSample] = []
        
        for idx, section in enumerate(sections, start=1):
            sample = self._build_training_sample(s_doc.doc_id, section, idx)
            samples.append(sample)

        # Compute document checksum from sample IDs to preserve structural boundaries
        doc_payload = ":".join(sample.sample_id for sample in samples)
        doc_checksum = hashlib.sha256(doc_payload.encode("utf-8")).hexdigest()
        
        # Generate deterministic document artifact ID using uuid5
        doc_artifact_id = uuid.uuid5(AURORA_NAMESPACE, f"doc_artifact:{s_doc.doc_id}:{doc_checksum}")

        doc_artifact = ArtifactMetadata(
            artifact_id=doc_artifact_id,
            parent_artifact_ids=[s_doc.artifact.artifact_id],
            derived_from=[s_doc.artifact.artifact_id],
            checksum=doc_checksum,
            created_at=s_doc.artifact.created_at,
            schema_version="1.0.0",
        )

        return TrainingDocument(
            doc_id=s_doc.doc_id,
            samples=samples,
            metadata=s_doc.metadata,
            artifact=doc_artifact,
        )

    def _group_sections(self, segments: List[DocumentSegment]) -> List[List[DocumentSegment]]:
        """Groups list of segments into sections starting with Heading segments or split on length to prevent truncation."""
        if not segments:
            raise ValueError("Cannot group empty list of segments.")

        sections: List[List[DocumentSegment]] = []
        current_section: List[DocumentSegment] = []
        current_length = 0

        for seg in segments:
            seg_len = len(seg.text)
            has_non_heading = any(s.type != SegmentType.HEADING for s in current_section)
            
            if (seg.type == SegmentType.HEADING and has_non_heading) or (current_section and current_length + seg_len > 2000):
                if current_section:
                    sections.append(current_section)
                current_section = [seg]
                current_length = seg_len
            else:
                current_section.append(seg)
                current_length += seg_len

        if current_section:
            sections.append(current_section)

        return sections

    def _build_training_sample(
        self, doc_id: str, section_segments: List[DocumentSegment], seq_num: int
    ) -> TrainingSample:
        """Constructs a TrainingSample from a list of grouped segments."""
        if not section_segments:
            raise ValueError("Cannot build a training sample from zero segments.")

        heading_segment: Optional[DocumentSegment] = None
        if section_segments[0].type == SegmentType.HEADING:
            heading_segment = section_segments[0]

        # Concatenate text exactly
        text = "".join(seg.text for seg in section_segments)

        page_numbers = self._collect_page_numbers(section_segments)

        heading_seg_id = heading_segment.segment_id if heading_segment else None
        source_seg_ids = [seg.segment_id for seg in section_segments]

        traceability = TrainingSampleTraceability(
            doc_id=doc_id,
            heading_segment_id=heading_seg_id,
            source_segment_ids=source_seg_ids,
            page_numbers=page_numbers,
        )

        heading_level = getattr(heading_segment, "level", None) if heading_segment else None
        heading_text = heading_segment.text if heading_segment else None
        expected_child_count = len(source_seg_ids) - 1 if heading_seg_id else len(source_seg_ids)
        metadata = TrainingSampleMetadata(
            heading_level=heading_level,
            child_count=expected_child_count,
            heading_text=heading_text,
        )

        sample_id = self._generate_sample_id(doc_id, heading_seg_id, source_seg_ids)

        return TrainingSample(
            sample_id=sample_id,
            sequence_number=seq_num,
            text=text,
            traceability=traceability,
            metadata=metadata,
        )

    def _generate_sample_id(
        self, doc_id: str, heading_segment_id: Optional[str], source_segment_ids: List[str]
    ) -> str:
        """Deterministically generates a sample ID hash from tracing inputs."""
        heading_id_str = heading_segment_id or ""
        ordered_ids_str = "".join(source_segment_ids)
        hash_input = f"{doc_id}{heading_id_str}{ordered_ids_str}"
        return hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

    def _collect_page_numbers(self, section_segments: List[DocumentSegment]) -> List[int]:
        """Extracts sorted, unique page numbers from segments."""
        pages_set = set()
        for seg in section_segments:
            if seg.source_reference and seg.source_reference.page_number is not None:
                pages_set.add(seg.source_reference.page_number)
        return sorted(pages_set)
