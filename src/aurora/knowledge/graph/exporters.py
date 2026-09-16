"""Exporters for serializing KnowledgeGraph in standard JSON or GraphML XML formats."""

import json

from aurora.models import KnowledgeGraph


class JsonExporter:
    """Exporter converting KnowledgeGraph to JSON string format."""

    def export(self, graph: KnowledgeGraph) -> str:
        data = {
            "graph_id": str(graph.graph_id),
            "namespace": graph.namespace,
            "graph_version": graph.graph_version,
            "concepts": [
                {
                    "concept_id": str(c.concept_id),
                    "canonical_name": c.canonical_name,
                    "aliases": c.aliases,
                    "subject": c.subject,
                    "difficulty": c.difficulty,
                    "metadata": c.metadata,
                }
                for c in graph.concepts.values()
            ],
            "units": [
                {
                    "unit_id": str(u.unit_id),
                    "type": u.type.value,
                    "title": u.title,
                    "content": u.content,
                    "occurrence_ids": [str(oid) for oid in u.occurrence_ids],
                    "evidence_ids": [str(eid) for eid in u.evidence_ids],
                    "metadata": u.metadata,
                }
                for u in graph.knowledge_units.values()
            ],
            "relationships": [
                {
                    "relationship_id": str(r.relationship_id),
                    "source_concept_id": str(r.source_concept_id),
                    "target_concept_id": str(r.target_concept_id),
                    "type": r.type.value,
                    "confidence": r.confidence,
                    "discovery_strategy": r.discovery_strategy,
                }
                for r in graph.relationships.values()
            ],
            "mappings": [
                {
                    "concept_id": str(m.concept_id),
                    "knowledge_unit_ids": [str(uid) for uid in m.knowledge_unit_ids],
                    "primary_unit": str(m.primary_unit) if m.primary_unit else None,
                    "confidence": m.confidence,
                }
                for m in graph.mappings.values()
            ],
            "statistics": graph.statistics.model_dump(),
        }
        return json.dumps(data, indent=2)


class GraphMLExporter:
    """Exporter converting KnowledgeGraph structure to GraphML XML string format."""

    def export(self, graph: KnowledgeGraph) -> str:
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<graphml xmlns="http://graphml.graphdrawing.org/xmlns"',
            '         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
            '         xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns',
            '         http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd">',
            '  <key id="label" for="node" attr.name="label" attr.type="string"/>',
            '  <key id="type" for="node" attr.name="type" attr.type="string"/>',
            '  <key id="rel_type" for="edge" attr.name="rel_type" attr.type="string"/>',
            f'  <graph id="{graph.graph_id}" edgedefault="directed">',
        ]

        # Export concept nodes
        for cid, concept in graph.concepts.items():
            lines.append(
                f'    <node id="{cid}">'
                f'<data key="label">{concept.canonical_name}</data>'
                f'<data key="type">concept</data>'
                f'</node>'
            )

        # Export knowledge unit nodes
        for uid, unit in graph.knowledge_units.items():
            title = unit.title or f"{unit.type.value} Unit"
            lines.append(
                f'    <node id="{uid}">'
                f'<data key="label">{title}</data>'
                f'<data key="type">unit</data>'
                f'</node>'
            )

        # Export relationship edges
        for r_id, rel in graph.relationships.items():
            src_id = rel.source_concept_id
            tgt_id = rel.target_concept_id
            lines.append(
                f'    <edge id="{r_id}" source="{src_id}" target="{tgt_id}">'
                f'<data key="rel_type">{rel.type.value}</data>'
                f'</edge>'
            )

        # Export mappings as concept-to-unit mapping edges
        for mapping in graph.mappings.values():
            for uid in mapping.knowledge_unit_ids:
                lines.append(
                    f'    <edge source="{mapping.concept_id}" target="{uid}">'
                    f'<data key="rel_type">MAPPED_TO</data>'
                    f'</edge>'
                )

        lines.extend([
            "  </graph>",
            "</graphml>",
        ])
        return "\n".join(lines)
