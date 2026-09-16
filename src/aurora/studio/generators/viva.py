"""Viva dataset generator plugin compiling oral exam viva questions."""

import uuid
from typing import List

from aurora.models import (
    DatasetCollection,
    DatasetExample,
    DatasetExampleTraceability,
)
from aurora.studio.context import DatasetGenerationContext
from aurora.studio.interfaces import GeneratorDescriptor


class VivaGenerator:
    """Viva Generator plugin transforming semantic chunks into oral exam formats."""

    @property
    def descriptor(self) -> GeneratorDescriptor:
        return GeneratorDescriptor(
            name="VivaGenerator",
            version="1.0.0",
            supported_formats=["viva"],
            template_version="1.0.0",
        )

    def generate(self, context: DatasetGenerationContext) -> DatasetCollection:
        examples: List[DatasetExample] = []
        template = context.template_registry.get("viva")
        if not template:
            raise KeyError("Viva prompt template not found in context registry.")

        for chunk in context.chunks.chunks:
            definition_text = "No definition provided."
            for unit in chunk.knowledge_units:
                if unit.type.value == "definition":
                    definition_text = unit.content
                    break

            prereqs_str = ", ".join(
                str(pid) for pid in chunk.prerequisites
            ) or "None"

            prompt = template.user_prompt_template.format(
                concept_name=chunk.concept_name,
                prerequisites=prereqs_str,
            )

            response = (
                f"Examiner: How does {chunk.concept_name} build on {prereqs_str}?\n"
                f"Student: Grounded in definition: {definition_text}."
            )

            traceability = DatasetExampleTraceability(
                knowledge_unit_ids=[u.unit_id for u in chunk.knowledge_units],
                concept_ids=[chunk.concept_id],
                relationship_ids=[
                    r.relationship_id for r in chunk.incoming_relationships
                ] + [
                    r.relationship_id for r in chunk.outgoing_relationships
                ],
                evidence_ids=chunk.evidence_ids,
                chunk_ids=[chunk.chunk_id],
            )

            example = DatasetExample(
                example_id=uuid.uuid5(uuid.NAMESPACE_DNS, f"viva:{chunk.chunk_id}"),
                format_tag="viva",
                input=prompt,
                output=response,
                supporting_context=definition_text,
                metadata={"difficulty": chunk.metadata.get("difficulty", "unknown")},
                traceability=traceability,
            )
            examples.append(example)

        return DatasetCollection(collection_id=uuid.uuid4(), examples=examples)
