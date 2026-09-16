"""Pipeline steps and orchestrator for assembling and validating the KnowledgeGraph."""

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

from aurora.core.exceptions import GraphConstructionError, InvalidGraphReferenceError
from aurora.core.pipeline import BasePipeline, PipelineContext, PipelineResult
from aurora.knowledge.graph.interfaces import GraphPayload, IGraphStep
from aurora.models import (
    ArtifactMetadata,
    ConceptRelationshipCollection,
    ExtractedConceptCollection,
    GraphStatistics,
    KnowledgeGraph,
    KnowledgeUnitCollection,
)


class GraphAssemblyStep(IGraphStep):
    """Indexes concepts, units, relationships, and mappings into dictionaries."""

    def process(
        self, input_data: GraphPayload, context: PipelineContext
    ) -> GraphPayload:
        indexed_concepts = {c.concept_id: c for c in input_data.concepts.concepts}
        indexed_units = {u.unit_id: u for u in input_data.units.units}
        indexed_relationships = {
            r.relationship_id: r for r in input_data.relationships.relationships
        }

        indexed_mappings = {}
        for m in input_data.units.mappings:
            map_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"{m.concept_id}")
            indexed_mappings[map_uuid] = m

        object.__setattr__(input_data, "indexed_concepts", indexed_concepts)
        object.__setattr__(input_data, "indexed_units", indexed_units)
        object.__setattr__(input_data, "indexed_relationships", indexed_relationships)
        object.__setattr__(input_data, "indexed_mappings", indexed_mappings)
        return input_data


class GraphValidationStep(IGraphStep):
    """Enforces referential integrity constraints across the assembled graph components."""

    def process(
        self, input_data: GraphPayload, context: PipelineContext
    ) -> GraphPayload:
        # Validate relationships refer to existing concept IDs
        for rel in input_data.indexed_relationships.values():
            if rel.source_concept_id not in input_data.indexed_concepts:
                raise InvalidGraphReferenceError(
                    f"Relationship '{rel.relationship_id}' source concept "
                    f"'{rel.source_concept_id}' does not exist in the graph."
                )
            if rel.target_concept_id not in input_data.indexed_concepts:
                raise InvalidGraphReferenceError(
                    f"Relationship '{rel.relationship_id}' target concept "
                    f"'{rel.target_concept_id}' does not exist in the graph."
                )

        # Validate mappings refer to existing concept and unit IDs
        for mapping in input_data.indexed_mappings.values():
            if mapping.concept_id not in input_data.indexed_concepts:
                raise InvalidGraphReferenceError(
                    f"Concept mapping references non-existent concept '{mapping.concept_id}'."
                )
            for unit_id in mapping.knowledge_unit_ids:
                if unit_id not in input_data.indexed_units:
                    raise InvalidGraphReferenceError(
                        f"Concept mapping references non-existent unit '{unit_id}'."
                    )

        return input_data


class GraphStatisticsStep(IGraphStep):
    """Computes quality and topological graph metrics."""

    def _dfs_cycle(
        self,
        node: uuid.UUID,
        adj: Dict[uuid.UUID, List[uuid.UUID]],
        visited: Set[uuid.UUID],
        stack: Set[uuid.UUID]
    ) -> bool:
        visited.add(node)
        stack.add(node)
        for neighbor in adj.get(node, []):
            if neighbor not in visited:
                if self._dfs_cycle(neighbor, adj, visited, stack):
                    return True
            elif neighbor in stack:
                return True
        stack.remove(node)
        return False

    def _count_cycles(
        self,
        nodes: List[uuid.UUID],
        adj: Dict[uuid.UUID, List[uuid.UUID]]
    ) -> int:
        visited: Set[uuid.UUID] = set()
        stack: Set[uuid.UUID] = set()
        cycles = 0
        for node in nodes:
            if node not in visited:
                if self._dfs_cycle(node, adj, visited, stack):
                    cycles += 1
        return cycles

    def _dfs_cc(
        self,
        node: uuid.UUID,
        adj: Dict[uuid.UUID, List[uuid.UUID]],
        visited: Set[uuid.UUID]
    ) -> None:
        visited.add(node)
        for neighbor in adj.get(node, []):
            if neighbor not in visited:
                self._dfs_cc(neighbor, adj, visited)

    def process(
        self, input_data: GraphPayload, context: PipelineContext
    ) -> GraphPayload:
        concepts = list(input_data.indexed_concepts.keys())
        relationships = input_data.indexed_relationships.values()

        # Build adjacency maps
        adj_dir: Dict[uuid.UUID, List[uuid.UUID]] = {c: [] for c in concepts}
        adj_undir: Dict[uuid.UUID, List[uuid.UUID]] = {c: [] for c in concepts}

        for rel in relationships:
            src, tgt = rel.source_concept_id, rel.target_concept_id
            if src in adj_dir and tgt in adj_dir:
                adj_dir[src].append(tgt)
                adj_undir[src].append(tgt)
                adj_undir[tgt].append(src)

        # 1. Connected components (undirected)
        visited_cc: Set[uuid.UUID] = set()
        cc_count = 0
        for node in concepts:
            if node not in visited_cc:
                cc_count += 1
                self._dfs_cc(node, adj_undir, visited_cc)

        # 2. Cycles (directed)
        cycles = self._count_cycles(concepts, adj_dir)

        # 3. Edge density
        n = len(concepts)
        density = (len(relationships) / (n * n)) if n > 0 else 0.0

        # 4. Orphan concepts (concepts with no relationships and no mapped units)
        mapped_concepts = {m.concept_id for m in input_data.indexed_mappings.values()}
        related_concepts: Set[uuid.UUID] = set()
        for rel in relationships:
            related_concepts.add(rel.source_concept_id)
            related_concepts.add(rel.target_concept_id)

        orphan_count = 0
        for cid in concepts:
            if cid not in mapped_concepts and cid not in related_concepts:
                orphan_count += 1

        stats = GraphStatistics(
            concept_count=n,
            relationship_count=len(relationships),
            knowledge_unit_count=len(input_data.indexed_units),
            edge_density=density,
            connected_components=cc_count,
            cycles_detected=cycles,
            orphan_concepts=orphan_count,
        )

        object.__setattr__(input_data, "statistics", stats)
        return input_data


class KnowledgeGraphBuilderPipeline(
    BasePipeline[
        Tuple[
            ExtractedConceptCollection,
            KnowledgeUnitCollection,
            ConceptRelationshipCollection
        ],
        KnowledgeGraph
    ]
):
    """Pipeline orchestrating sequential assembly, validation, and metrics reporting."""

    def __init__(self, steps: Optional[List[IGraphStep]] = None) -> None:
        if steps is None:
            default_steps: List[IGraphStep] = [
                GraphAssemblyStep(),
                GraphValidationStep(),
                GraphStatisticsStep(),
            ]
            super().__init__(default_steps)  # type: ignore
        else:
            super().__init__(steps)  # type: ignore

    def execute(
        self,
        input_data: Tuple[
            ExtractedConceptCollection,
            KnowledgeUnitCollection,
            ConceptRelationshipCollection
        ],
        context: PipelineContext,
    ) -> PipelineResult[KnowledgeGraph]:
        concepts_col, units_col, rels_col = input_data
        payload = GraphPayload(
            concepts=concepts_col,
            units=units_col,
            relationships=rels_col,
        )

        try:
            for step in self.steps:
                payload = step.process(payload, context)
        except Exception as e:
            if not isinstance(e, GraphConstructionError):
                raise GraphConstructionError(f"Graph construction failed: {e}") from e
            raise

        sig_input = "".join(str(cid) for cid in payload.indexed_concepts.keys())
        checksum = hashlib.sha256(sig_input.encode("utf-8")).hexdigest()

        artifact = ArtifactMetadata(
            artifact_id=uuid.uuid4(),
            parent_artifact_ids=[
                concepts_col.artifact.artifact_id,
                units_col.artifact.artifact_id,
                rels_col.artifact.artifact_id,
            ],
            derived_from=[
                concepts_col.artifact.artifact_id,
                units_col.artifact.artifact_id,
                rels_col.artifact.artifact_id,
            ],
            checksum=checksum,
            created_at=datetime.now(timezone.utc),
            schema_version="1.0.0",
        )

        # Graph ID derived from namespace name
        graph_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, rels_col.graph_namespace)

        assert payload.statistics is not None

        graph = KnowledgeGraph(
            graph_id=graph_uuid,
            namespace=rels_col.graph_namespace,
            concepts=payload.indexed_concepts,
            knowledge_units=payload.indexed_units,
            relationships=payload.indexed_relationships,
            mappings=payload.indexed_mappings,
            statistics=payload.statistics,
            artifact=artifact,
        )

        return PipelineResult(
            result=graph,
            metrics=context.metrics,
            warnings=context.warnings,
            diagnostics=context.diagnostics,
        )
