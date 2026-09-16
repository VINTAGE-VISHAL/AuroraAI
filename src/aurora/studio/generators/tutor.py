"""Tutor QA dataset generator plugin compiling tutor-style conversation examples."""

import uuid
from typing import List

from aurora.models import (
    DatasetCollection,
    DatasetExample,
    DatasetExampleTraceability,
)
from aurora.studio.context import DatasetGenerationContext
from aurora.studio.interfaces import GeneratorDescriptor


class TutorGenerator:
    """Tutor Generator plugin transforming semantic chunks into QA tuning formats."""

    @property
    def descriptor(self) -> GeneratorDescriptor:
        return GeneratorDescriptor(
            name="TutorGenerator",
            version="1.0.0",
            supported_formats=["tutor"],
            template_version="1.0.0",
        )

    def generate(self, context: DatasetGenerationContext) -> DatasetCollection:
        examples: List[DatasetExample] = []
        template = context.template_registry.get("tutor")
        if not template:
            raise KeyError("Tutor prompt template not found in context registry.")

        for chunk in context.chunks.chunks:
            # Pedagogical rule extraction
            # Tutor rule: extract definition block if present
            definition_text = "No definition provided."
            for unit in chunk.knowledge_units:
                if unit.type.value == "definition":
                    definition_text = unit.content
                    break

            prereqs_str = ", ".join(
                str(pid) for pid in chunk.prerequisites
            ) or "None"

            # Format template parameters
            prompt = template.user_prompt_template.format(
                concept_name=chunk.concept_name,
                definition=definition_text,
                prerequisites=prereqs_str,
            )

            response = (
                f"Let's learn about {chunk.concept_name}. "
                f"Here is the definition: {definition_text}. "
                f"Before this, you should know: {prereqs_str}."
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
                example_id=uuid.uuid5(uuid.NAMESPACE_DNS, f"tutor:{chunk.chunk_id}"),
                format_tag="tutor",
                input=prompt,
                output=response,
                supporting_context=definition_text,
                metadata={"difficulty": chunk.metadata.get("difficulty", "unknown")},
                traceability=traceability,
            )
            examples.append(example)

        return DatasetCollection(collection_id=uuid.uuid4(), examples=examples)
