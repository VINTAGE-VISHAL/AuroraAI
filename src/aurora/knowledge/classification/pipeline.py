"""Pipeline components and orchestrator for educational content classification."""

import hashlib
import re
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from aurora.core.exceptions import AuroraError
from aurora.core.pipeline import BasePipeline, PipelineContext, PipelineResult
from aurora.knowledge.classification.interfaces import ClassificationPayload, IClassificationStep
from aurora.models import (
    ArtifactMetadata,
    ConceptKnowledgeMapping,
    ConceptOccurrence,
    Evidence,
    ExtractedConceptCollection,
    KnowledgeType,
    KnowledgeUnit,
    KnowledgeUnitCollection,
    StructuredDocument,
)
from aurora.models.enums import SegmentType


class CandidateUnitDiscoveryStep(IClassificationStep):
    """Identifies document segments eligible to become learning units."""

    def process(
        self, input_data: ClassificationPayload, context: PipelineContext
    ) -> ClassificationPayload:
        candidates = []
        for seg in input_data.document.segments:
            # We classify paragraphs, code blocks, and list segments
            if seg.type in (SegmentType.PARAGRAPH, SegmentType.CODE_BLOCK, SegmentType.METADATA):
                if len(seg.text.strip()) > 3:
                    candidates.append(seg)
        input_data.candidate_segments = candidates
        return input_data


class KnowledgeTypeClassificationStep(IClassificationStep):
    """Classifies candidate segments into structured KnowledgeTypes using keywords."""

    PATTERN_MAP = {
        KnowledgeType.DEFINITION: re.compile(r"\b(?:Definition|Def\.?)\s*:", re.IGNORECASE),
        KnowledgeType.EXAMPLE: re.compile(r"\b(?:Example|Eg\.?)\s*:", re.IGNORECASE),
        KnowledgeType.ALGORITHM: re.compile(r"\b(?:Algorithm|Procedure)\s*:", re.IGNORECASE),
        KnowledgeType.EXERCISE: re.compile(r"\b(?:Exercise|Question)\s*:", re.IGNORECASE),
        KnowledgeType.THEOREM: re.compile(r"\b(?:Theorem)\s*:", re.IGNORECASE),
        KnowledgeType.PROOF: re.compile(r"\b(?:Proof)\s*:", re.IGNORECASE),
        KnowledgeType.WARNING: re.compile(r"\b(?:Warning|Caution)\s*:", re.IGNORECASE),
    }

    def process(
        self, input_data: ClassificationPayload, context: PipelineContext
    ) -> ClassificationPayload:
        classified = {}
        for seg in input_data.candidate_segments:
            assigned_type = KnowledgeType.NOTE
            for k_type, pattern in self.PATTERN_MAP.items():
                if pattern.search(seg.text):
                    assigned_type = k_type
                    break
            classified[seg.segment_id] = assigned_type
        input_data.classified_types = classified
        return input_data


class ConceptAssociationStep(IClassificationStep):
    """Associates classified segments with Concepts from the taxonomy."""

    def process(
        self, input_data: ClassificationPayload, context: PipelineContext
    ) -> ClassificationPayload:
        occurrences: List[ConceptOccurrence] = []
        evidences: List[Evidence] = []
        unit_map: Dict[uuid.UUID, List[uuid.UUID]] = {}  # concept_id -> List[unit_id]

        occurrence_counter = 0

        for seg in input_data.candidate_segments:
            seg_type = input_data.classified_types.get(seg.segment_id, KnowledgeType.NOTE)
            # Create a deterministic UUID for the knowledge unit
            unit_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"{seg.segment_id}:{seg_type}")

            # Check if any concept names or aliases are mentioned in the text
            associated_concept_ids = []
            for concept in input_data.concepts.concepts:
                # Compile regex matching word boundaries for canonical name and aliases
                terms = [concept.canonical_name] + concept.aliases
                for term in terms:
                    pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
                    match = pattern.search(seg.text)
                    if match:
                        occurrence_counter += 1
                        occ_uuid = uuid.uuid5(
                            uuid.NAMESPACE_DNS,
                            f"{seg.segment_id}:{concept.concept_id}:{occurrence_counter}"
                        )
                        ev_uuid = uuid.uuid5(
                            uuid.NAMESPACE_DNS,
                            f"evidence:{occ_uuid}"
                        )

                        occ = ConceptOccurrence(
                            occurrence_id=occ_uuid,
                            concept_id=concept.concept_id,
                            segment_id=seg.segment_id,
                            page_number=None,
                            confidence=1.0,
                            matched_text=match.group(0),
                            strategy="RegexMentionsMatcher",
                            occurrence_order=occurrence_counter,
                        )
                        occurrences.append(occ)

                        ev = Evidence(
                            evidence_id=ev_uuid,
                            target_type="Concept",
                            target_id=concept.concept_id,
                            segment_id=seg.segment_id,
                            page_number=None,
                            matched_text=match.group(0),
                            strategy="RegexMentionsMatcher",
                            confidence=1.0,
                        )
                        evidences.append(ev)

                        associated_concept_ids.append(concept.concept_id)
                        if concept.concept_id not in unit_map:
                            unit_map[concept.concept_id] = []
                        unit_map[concept.concept_id].append(unit_uuid)
                        break  # Match found for this concept, continue to next concept

            # Construct KnowledgeUnit
            unit_occ_ids = [o.occurrence_id for o in occurrences if o.segment_id == seg.segment_id]
            unit_ev_ids = [e.evidence_id for e in evidences if e.segment_id == seg.segment_id]

            # Set a descriptive title if matched
            title = f"{seg_type.value} Block"

            unit = KnowledgeUnit(
                unit_id=unit_uuid,
                type=seg_type,
                title=title,
                content=seg.text,
                occurrence_ids=unit_occ_ids,
                evidence_ids=unit_ev_ids,
                metadata={"segment_index": seg.segment_index},
            )
            input_data.units.append(unit)

        # Build final mappings List
        mappings = []
        for c_id, u_ids in unit_map.items():
            mappings.append(
                ConceptKnowledgeMapping(
                    concept_id=c_id,
                    knowledge_unit_ids=u_ids,
                    primary_unit=u_ids[0] if u_ids else None,
                    confidence=1.0,
                )
            )

        input_data.occurrences = occurrences
        input_data.evidences = evidences
        input_data.mappings = mappings
        return input_data


class CollectionAssemblyStep(IClassificationStep):
    """Produces the final immutable KnowledgeUnitCollection with lineage tracking."""

    def process(
        self, input_data: ClassificationPayload, context: PipelineContext
    ) -> ClassificationPayload:
        # Collect unit IDs signatures for deterministic checksumming
        sig_input = "".join(str(u.unit_id) for u in input_data.units)
        checksum = hashlib.sha256(sig_input.encode("utf-8")).hexdigest()

        artifact = ArtifactMetadata(
            artifact_id=uuid.uuid4(),
            parent_artifact_ids=[
                input_data.concepts.artifact.artifact_id,
                input_data.document.artifact.artifact_id,
            ],
            derived_from=[
                input_data.concepts.artifact.artifact_id,
                input_data.document.artifact.artifact_id,
            ],
            checksum=checksum,
            created_at=datetime.now(timezone.utc),
            schema_version="1.0.0",
        )

        collection = KnowledgeUnitCollection(
            collection_id=uuid.uuid4(),
            source_document_id=input_data.document.doc_id,
            units=input_data.units,
            mappings=input_data.mappings,
            occurrences=input_data.occurrences,
            evidences=input_data.evidences,
            artifact=artifact,
        )
        context.diagnostics["final_collection"] = collection
        return input_data


class KnowledgeUnitClassifierPipeline(
    BasePipeline[Tuple[ExtractedConceptCollection, StructuredDocument], KnowledgeUnitCollection]
):
    """Coordinates sequentially discovering, classifying, and mapping knowledge units."""

    def __init__(self, steps: Optional[List[IClassificationStep]] = None) -> None:
        if steps is None:
            default_steps: List[IClassificationStep] = [
                CandidateUnitDiscoveryStep(),
                KnowledgeTypeClassificationStep(),
                ConceptAssociationStep(),
                CollectionAssemblyStep(),
            ]
            super().__init__(default_steps)  # type: ignore
        else:
            super().__init__(steps)  # type: ignore

    def execute(
        self,
        input_data: Tuple[ExtractedConceptCollection, StructuredDocument],
        context: PipelineContext,
    ) -> PipelineResult[KnowledgeUnitCollection]:
        concepts, doc = input_data
        payload = ClassificationPayload(concepts=concepts, document=doc)

        try:
            for step in self.steps:
                payload = step.process(payload, context)
        except Exception as e:
            raise AuroraError(f"Classification pipeline failed: {e}") from e

        collection = context.diagnostics.get("final_collection")
        if not isinstance(collection, KnowledgeUnitCollection):
            raise AuroraError("Pipeline failed to assemble KnowledgeUnitCollection.")

        return PipelineResult(
            result=collection,
            metrics=context.metrics,
            warnings=context.warnings,
            diagnostics=context.diagnostics,
        )
