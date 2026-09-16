"""Pipeline steps and orchestrator for building SemanticChunk collections."""

import hashlib
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Set

from aurora.core.exceptions import AuroraError
from aurora.core.pipeline import BasePipeline, PipelineContext, PipelineResult
from aurora.knowledge.chunk.interfaces import ChunkPayload, IChunkStep
from aurora.models import (
    ArtifactMetadata,
    ConceptRelationship,
    KnowledgeGraph,
    KnowledgeUnit,
    RelationshipType,
    SemanticChunk,
    SemanticChunkCollection,
)


class ConceptGroupingStep(IChunkStep):
    """Creates a basic SemanticChunk container for each concept in the graph."""

    def process(
        self, input_data: ChunkPayload, context: PipelineContext
    ) -> ChunkPayload:
        chunks: List[SemanticChunk] = []

        for cid, concept in input_data.graph.concepts.items():
            chunk = SemanticChunk(
                chunk_id=uuid.uuid4(),
                concept_id=cid,
                concept_name=concept.canonical_name,
                metadata={
                    "subject": concept.subject,
                    "difficulty": concept.difficulty,
                },
            )
            chunks.append(chunk)

        object.__setattr__(input_data, "chunks", chunks)
        return input_data


class KnowledgeUnitAggregationStep(IChunkStep):
    """Collects knowledge units and evidence IDs mapped to each concept chunk."""

    def process(
        self, input_data: ChunkPayload, context: PipelineContext
    ) -> ChunkPayload:
        updated_chunks: List[SemanticChunk] = []
        graph = input_data.graph

        for chunk in input_data.chunks:
            # Look up concept knowledge mappings
            mapping = None
            for m in graph.mappings.values():
                if m.concept_id == chunk.concept_id:
                    mapping = m
                    break

            units: List[KnowledgeUnit] = []
            ev_ids: Set[uuid.UUID] = set()

            if mapping is not None:
                for uid in mapping.knowledge_unit_ids:
                    if uid in graph.knowledge_units:
                        unit = graph.knowledge_units[uid]
                        units.append(unit)
                        # Add occurrences/evidence IDs associated with this unit
                        for ev_id in unit.evidence_ids:
                            ev_ids.add(ev_id)

            new_chunk = SemanticChunk(
                chunk_id=chunk.chunk_id,
                concept_id=chunk.concept_id,
                concept_name=chunk.concept_name,
                knowledge_units=units,
                incoming_relationships=chunk.incoming_relationships,
                outgoing_relationships=chunk.outgoing_relationships,
                prerequisites=chunk.prerequisites,
                evidence_ids=list(ev_ids),
                metadata=chunk.metadata,
            )
            updated_chunks.append(new_chunk)

        object.__setattr__(input_data, "chunks", updated_chunks)
        return input_data


class RelationshipExpansionStep(IChunkStep):
    """Enriches each chunk with its incoming, outgoing, and prerequisite relationships."""

    def process(
        self, input_data: ChunkPayload, context: PipelineContext
    ) -> ChunkPayload:
        updated_chunks: List[SemanticChunk] = []
        graph = input_data.graph

        for chunk in input_data.chunks:
            incoming: List[ConceptRelationship] = []
            outgoing: List[ConceptRelationship] = []
            prereqs: Set[uuid.UUID] = set()

            for rel in graph.relationships.values():
                if rel.target_concept_id == chunk.concept_id:
                    incoming.append(rel)
                    if rel.type in (
                        RelationshipType.DEPENDS_ON,
                        RelationshipType.PREREQUISITE_OF,
                    ):
                        prereqs.add(rel.source_concept_id)
                elif rel.source_concept_id == chunk.concept_id:
                    outgoing.append(rel)

            new_chunk = SemanticChunk(
                chunk_id=chunk.chunk_id,
                concept_id=chunk.concept_id,
                concept_name=chunk.concept_name,
                knowledge_units=chunk.knowledge_units,
                incoming_relationships=incoming,
                outgoing_relationships=outgoing,
                prerequisites=list(prereqs),
                evidence_ids=chunk.evidence_ids,
                metadata=chunk.metadata,
            )
            updated_chunks.append(new_chunk)

        object.__setattr__(input_data, "chunks", updated_chunks)
        return input_data


class ChunkValidationStep(IChunkStep):
    """Verifies that each chunk is valid and tags structural issues in metadata."""

    def process(
        self, input_data: ChunkPayload, context: PipelineContext
    ) -> ChunkPayload:
        for chunk in input_data.chunks:
            if not chunk.knowledge_units:
                context.warnings.append(
                    f"SemanticChunk '{chunk.concept_name}' ({chunk.concept_id}) "
                    f"lacks mapped Knowledge Units."
                )
                chunk.metadata["has_warnings"] = True
        return input_data


class ChunkAssemblyStep(IChunkStep):
    """Assembles final semantic chunks into a versioned SemanticChunkCollection."""

    def process(
        self, input_data: ChunkPayload, context: PipelineContext
    ) -> ChunkPayload:
        sig_input = "".join(str(c.chunk_id) for c in input_data.chunks)
        checksum = hashlib.sha256(sig_input.encode("utf-8")).hexdigest()

        artifact = ArtifactMetadata(
            artifact_id=uuid.uuid4(),
            parent_artifact_ids=[input_data.graph.artifact.artifact_id],
            derived_from=[input_data.graph.artifact.artifact_id],
            checksum=checksum,
            created_at=datetime.now(timezone.utc),
            schema_version="1.0.0",
        )

        collection = SemanticChunkCollection(
            collection_id=uuid.uuid4(),
            chunks=input_data.chunks,
            artifact=artifact,
        )

        context.diagnostics["final_chunks"] = collection
        return input_data


class SemanticChunkBuilderPipeline(
    BasePipeline[KnowledgeGraph, SemanticChunkCollection]
):
    """Pipeline coordinating the generation of self-contained semantic learning chunks."""

    def __init__(self, steps: Optional[List[IChunkStep]] = None) -> None:
        if steps is None:
            default_steps: List[IChunkStep] = [
                ConceptGroupingStep(),
                KnowledgeUnitAggregationStep(),
                RelationshipExpansionStep(),
                ChunkValidationStep(),
                ChunkAssemblyStep(),
            ]
            super().__init__(default_steps)  # type: ignore
        else:
            super().__init__(steps)  # type: ignore

    def execute(
        self,
        input_data: KnowledgeGraph,
        context: PipelineContext,
    ) -> PipelineResult[SemanticChunkCollection]:
        payload = ChunkPayload(graph=input_data)

        try:
            for step in self.steps:
                payload = step.process(payload, context)
        except Exception as e:
            raise AuroraError(f"Semantic chunk build failed: {e}") from e

        collection = context.diagnostics.get("final_chunks")
        if not isinstance(collection, SemanticChunkCollection):
            raise AuroraError("Pipeline failed to assemble SemanticChunkCollection.")

        return PipelineResult(
            result=collection,
            metrics=context.metrics,
            warnings=context.warnings,
            diagnostics=context.diagnostics,
        )
