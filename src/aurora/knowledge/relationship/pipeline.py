"""Pipeline components and orchestrator for extracting concept relationships."""

import hashlib
import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Set, Tuple

from aurora.core.exceptions import AuroraError
from aurora.core.pipeline import BasePipeline, PipelineContext, PipelineResult
from aurora.knowledge.relationship.interfaces import (
    IRelationshipStep,
    RelationshipCandidate,
    RelationshipPayload,
)
from aurora.models import (
    ArtifactMetadata,
    Concept,
    ConceptRelationship,
    ConceptRelationshipCollection,
    Evidence,
    ExtractedConceptCollection,
    KnowledgeUnit,
    KnowledgeUnitCollection,
    RelationshipType,
    StructuredDocument,
)


class RelationshipPattern:
    """Pattern rule for classifying relationships from text matching."""

    def __init__(
        self,
        pattern_str: str,
        relationship_type: RelationshipType,
        confidence: float,
        reverse_direction: bool = False,
    ) -> None:
        self.pattern = re.compile(pattern_str, re.IGNORECASE)
        self.relationship_type = relationship_type
        self.confidence = confidence
        self.reverse_direction = reverse_direction


class CandidateRelationshipDiscoveryStep(IRelationshipStep):
    """Discovers relationship candidates from hierarchy, patterns, and co-occurrences."""

    PATTERNS = [
        RelationshipPattern(
            r"\b([A-Za-z0-9\s\-]+)\s+(?:depends\s+on|requires|needs)\s+([A-Za-z0-9\s\-]+)\b",
            RelationshipType.DEPENDS_ON,
            0.90,
        ),
        RelationshipPattern(
            r"\b([A-Za-z0-9\s\-]+)\s+(?:is\s+required\s+for|is\s+needed\s+by)\s+([A-Za-z0-9\s\-]+)\b",
            RelationshipType.DEPENDS_ON,
            0.90,
            reverse_direction=True,
        ),
        RelationshipPattern(
            r"\b([A-Za-z0-9\s\-]+)\s+(?:consists\s+of|is\s+part\s+of)\s+([A-Za-z0-9\s\-]+)\b",
            RelationshipType.PART_OF,
            0.90,
        ),
        RelationshipPattern(
            r"\b([A-Za-z0-9\s\-]+)\s+(?:is\s+a\s+subtype\s+of|is\s+a\s+kind\s+of)\s+([A-Za-z0-9\s\-]+)\b",
            RelationshipType.SUBTYPE_OF,
            0.90,
        ),
        RelationshipPattern(
            r"\b([A-Za-z0-9\s\-]+)\s+(?:references|refers\s+to|ref\.?)\s+([A-Za-z0-9\s\-]+)\b",
            RelationshipType.REFERENCES,
            0.80,
        ),
    ]

    def _find_concept_by_name(
        self, text: str, payload: RelationshipPayload
    ) -> Optional[uuid.UUID]:
        """Resolves a text string to a concept ID using names or aliases."""
        cleaned = text.strip().lower()
        for concept in payload.concepts.concepts:
            terms = [concept.canonical_name.lower()] + [a.lower() for a in concept.aliases]
            if cleaned in terms:
                return concept.concept_id
        return None

    def _resolve_heading_concept(
        self, text: str, concepts: List[Concept]
    ) -> Optional[uuid.UUID]:
        """Resolves heading text to concept ID."""
        for concept in concepts:
            terms = [concept.canonical_name.lower()] + [
                a.lower() for a in concept.aliases
            ]
            if any(t in text.lower() for t in terms):
                return concept.concept_id
        return None

    def _check_hierarchy_mention(
        self,
        unit: KnowledgeUnit,
        seg_id: str,
        heading_concept_id: uuid.UUID,
        concepts: List[Concept],
        candidates: List[RelationshipCandidate],
    ) -> None:
        """Finds mentions of other concepts within child segments."""
        for concept in concepts:
            if concept.concept_id == heading_concept_id:
                continue
            terms = [concept.canonical_name.lower()] + [
                a.lower() for a in concept.aliases
            ]
            for term in terms:
                match = re.search(
                    rf"\b{re.escape(term)}\b", unit.content, re.IGNORECASE
                )
                if match:
                    candidates.append(
                        RelationshipCandidate(
                            source_concept_id=heading_concept_id,
                            target_concept_id=concept.concept_id,
                            context_segment_id=seg_id,
                            context_text=unit.content,
                            discovery_strategy="Hierarchy",
                            confidence=0.95,
                            matched_span_start=match.start(),
                            matched_span_end=match.end(),
                        )
                    )

    def _discover_hierarchy(
        self,
        input_data: RelationshipPayload,
        candidates: List[RelationshipCandidate]
    ) -> None:
        """Finds concepts that appear under a heading concept in the document layout."""
        concepts = input_data.concepts.concepts
        current_heading_concept_id: Optional[uuid.UUID] = None

        for unit in input_data.units.units:
            seg_idx = unit.metadata.get("segment_index")
            if seg_idx is None:
                continue
            seg = input_data.document.segments[seg_idx]
            if seg.text.startswith("#"):
                current_heading_concept_id = self._resolve_heading_concept(seg.text, concepts)
            elif current_heading_concept_id is not None:
                self._check_hierarchy_mention(
                    unit, seg.segment_id, current_heading_concept_id, concepts, candidates
                )

    def _discover_patterns(
        self,
        input_data: RelationshipPayload,
        candidates: List[RelationshipCandidate]
    ) -> None:
        """Finds relationships from sentence matching patterns."""
        for unit in input_data.units.units:
            for pattern_rule in self.PATTERNS:
                for match in pattern_rule.pattern.finditer(unit.content):
                    src_text = match.group(1)
                    tgt_text = match.group(2)

                    src_id = self._find_concept_by_name(src_text, input_data)
                    tgt_id = self._find_concept_by_name(tgt_text, input_data)

                    if src_id and tgt_id and src_id != tgt_id:
                        if pattern_rule.reverse_direction:
                            source, target = tgt_id, src_id
                        else:
                            source, target = src_id, tgt_id

                        strat = "Pattern:" + pattern_rule.relationship_type.value
                        candidates.append(
                            RelationshipCandidate(
                                source_concept_id=source,
                                target_concept_id=target,
                                context_segment_id=str(unit.unit_id),
                                context_text=unit.content,
                                discovery_strategy=strat,
                                confidence=pattern_rule.confidence,
                                matched_span_start=match.start(),
                                matched_span_end=match.end(),
                            )
                        )

    def _discover_co_occurrences(
        self,
        input_data: RelationshipPayload,
        candidates: List[RelationshipCandidate]
    ) -> None:
        """Finds co-occurrences of concepts inside a single unit block."""
        concepts = input_data.concepts.concepts
        for unit in input_data.units.units:
            mentioned = []
            for concept in concepts:
                terms = [concept.canonical_name.lower()] + [
                    a.lower() for a in concept.aliases
                ]
                for term in terms:
                    match = re.search(
                        rf"\b{re.escape(term)}\b", unit.content, re.IGNORECASE
                    )
                    if match:
                        mentioned.append((concept.concept_id, match))
                        break

            if len(mentioned) >= 2:
                for i in range(len(mentioned)):
                    for j in range(i + 1, len(mentioned)):
                        c1_id, m1 = mentioned[i]
                        c2_id, m2 = mentioned[j]
                        exists = any(
                            (c.source_concept_id == c1_id and c.target_concept_id == c2_id)
                            or (c.source_concept_id == c2_id and c.target_concept_id == c1_id)
                            for c in candidates
                        )
                        if not exists:
                            candidates.append(
                                RelationshipCandidate(
                                    source_concept_id=c1_id,
                                    target_concept_id=c2_id,
                                    context_segment_id=str(unit.unit_id),
                                    context_text=unit.content,
                                    discovery_strategy="Co-occurrence",
                                    confidence=0.60,
                                    matched_span_start=min(m1.start(), m2.start()),
                                    matched_span_end=max(m1.end(), m2.end()),
                                )
                            )

    def process(
        self, input_data: RelationshipPayload, context: PipelineContext
    ) -> RelationshipPayload:
        candidates: List[RelationshipCandidate] = []
        self._discover_hierarchy(input_data, candidates)
        self._discover_patterns(input_data, candidates)
        self._discover_co_occurrences(input_data, candidates)

        # Mutate payload candidates
        object.__setattr__(input_data, "candidates", candidates)
        return input_data


class RelationshipClassificationStep(IRelationshipStep):
    """Translates candidates into ConceptRelationship instances."""

    def process(
        self, input_data: RelationshipPayload, context: PipelineContext
    ) -> RelationshipPayload:
        relationships: List[ConceptRelationship] = []

        for cand in input_data.candidates:
            # Map relationship type based on discovery strategy
            rel_type = RelationshipType.RELATED_TO
            if cand.discovery_strategy.startswith("Pattern:"):
                type_str = cand.discovery_strategy.split(":")[1]
                rel_type = RelationshipType(type_str)
            elif cand.discovery_strategy == "Hierarchy":
                rel_type = RelationshipType.REFERENCES

            rel_uuid = uuid.uuid5(
                uuid.NAMESPACE_DNS,
                f"{cand.source_concept_id}:{cand.target_concept_id}:{rel_type.value}"
            )

            rel = ConceptRelationship(
                relationship_id=rel_uuid,
                source_concept_id=cand.source_concept_id,
                target_concept_id=cand.target_concept_id,
                type=rel_type,
                confidence=cand.confidence,
                discovery_strategy=cand.discovery_strategy,
                created_by_pipeline="ConceptRelationshipExtractorPipeline",
            )
            relationships.append(rel)

        object.__setattr__(input_data, "relationships", relationships)
        return input_data


class EvidenceAssociationStep(IRelationshipStep):
    """Constructs Evidence records linking relationships to matched spans."""

    def process(
        self, input_data: RelationshipPayload, context: PipelineContext
    ) -> RelationshipPayload:
        evidences: List[Evidence] = []

        for cand, rel in zip(
            input_data.candidates, input_data.relationships, strict=True
        ):
            ev_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"evidence:{rel.relationship_id}")
            ev = Evidence(
                evidence_id=ev_uuid,
                target_type="Relationship",
                target_id=rel.relationship_id,
                segment_id=cand.context_segment_id,
                page_number=None,
                matched_text=cand.context_text,
                matched_span_start=cand.matched_span_start,
                matched_span_end=cand.matched_span_end,
                strategy=cand.discovery_strategy,
                confidence=cand.confidence,
            )
            evidences.append(ev)

        object.__setattr__(input_data, "evidences", evidences)
        return input_data


class RelationshipValidationStep(IRelationshipStep):
    """Filters self-loops, normalizes duplicate edges, and filters below threshold."""

    def process(
        self, input_data: RelationshipPayload, context: PipelineContext
    ) -> RelationshipPayload:
        validated_rels: List[ConceptRelationship] = []
        validated_evs: List[Evidence] = []

        seen_edges: Set[Tuple[uuid.UUID, uuid.UUID]] = set()

        threshold = context.metrics.get("confidence_threshold", 0.50)

        for rel, ev in zip(
            input_data.relationships, input_data.evidences, strict=True
        ):
            # 1. Reject self-loops
            if rel.source_concept_id == rel.target_concept_id:
                continue

            # 2. Confidence threshold
            if rel.confidence < threshold:
                continue

            # 3. Direction & duplicate normalization
            # Collapse duplicates: keep the edge with the highest confidence
            # Sort node IDs to check undirected duplicates
            edge = tuple(sorted([rel.source_concept_id, rel.target_concept_id]))

            # For this simplified check, if we've seen this pair, we skip the lower confidence one
            # Because lists are processed sequentially, we keep the first one
            # (or we can sort them beforehand)
            if edge in seen_edges:
                continue

            seen_edges.add((rel.source_concept_id, rel.target_concept_id))
            validated_rels.append(rel)
            validated_evs.append(ev)

        object.__setattr__(input_data, "relationships", validated_rels)
        object.__setattr__(input_data, "evidences", validated_evs)
        return input_data


class CollectionAssemblyStep(IRelationshipStep):
    """Assembles final verified ConceptRelationshipCollection."""

    def process(
        self, input_data: RelationshipPayload, context: PipelineContext
    ) -> RelationshipPayload:
        sig_input = "".join(str(r.relationship_id) for r in input_data.relationships)
        checksum = hashlib.sha256(sig_input.encode("utf-8")).hexdigest()

        artifact = ArtifactMetadata(
            artifact_id=uuid.uuid4(),
            parent_artifact_ids=[
                input_data.concepts.artifact.artifact_id,
                input_data.units.artifact.artifact_id,
            ],
            derived_from=[
                input_data.concepts.artifact.artifact_id,
                input_data.units.artifact.artifact_id,
            ],
            checksum=checksum,
            created_at=datetime.now(timezone.utc),
            schema_version="1.0.0",
        )

        collection = ConceptRelationshipCollection(
            collection_id=uuid.uuid4(),
            source_document_id=input_data.concepts.source_document_id,
            graph_namespace=input_data.graph_namespace,
            relationships=input_data.relationships,
            evidences=input_data.evidences,
            artifact=artifact,
        )

        context.diagnostics["final_collection"] = collection
        return input_data


class ConceptRelationshipExtractorPipeline(
    BasePipeline[
        Tuple[ExtractedConceptCollection, KnowledgeUnitCollection, StructuredDocument],
        ConceptRelationshipCollection
    ]
):
    """Orchestrates sequential concept relationship candidate discovery and validation."""

    def __init__(
        self, graph_namespace: str, steps: Optional[List[IRelationshipStep]] = None
    ) -> None:
        self.graph_namespace = graph_namespace
        if steps is None:
            default_steps: List[IRelationshipStep] = [
                CandidateRelationshipDiscoveryStep(),
                RelationshipClassificationStep(),
                EvidenceAssociationStep(),
                RelationshipValidationStep(),
                CollectionAssemblyStep(),
            ]
            super().__init__(default_steps)  # type: ignore
        else:
            super().__init__(steps)  # type: ignore

    def execute(
        self,
        input_data: Tuple[
            ExtractedConceptCollection, KnowledgeUnitCollection, StructuredDocument
        ],
        context: PipelineContext,
    ) -> PipelineResult[ConceptRelationshipCollection]:
        concepts, units, doc = input_data
        payload = RelationshipPayload(
            concepts=concepts,
            units=units,
            document=doc,
            graph_namespace=self.graph_namespace,
        )

        try:
            for step in self.steps:
                payload = step.process(payload, context)
        except Exception as e:
            raise AuroraError(f"Relationship extraction failed: {e}") from e

        collection = context.diagnostics.get("final_collection")
        if not isinstance(collection, ConceptRelationshipCollection):
            raise AuroraError("Pipeline failed to assemble ConceptRelationshipCollection.")

        return PipelineResult(
            result=collection,
            metrics=context.metrics,
            warnings=context.warnings,
            diagnostics=context.diagnostics,
        )
