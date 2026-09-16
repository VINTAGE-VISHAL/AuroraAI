"""Unit tests for Dataset Studio validators."""

import uuid

from aurora.models import (
    DatasetCollection,
    DatasetExample,
    DatasetExampleTraceability,
)
from aurora.studio.validators import EducationalValidator, StructuralValidator


def test_dataset_validators() -> None:
    """Verify structural completeness and educational groundedness validation."""
    struct_val = StructuralValidator()
    edu_val = EducationalValidator()

    ex1 = DatasetExample(
        example_id=uuid.uuid4(),
        format_tag="mcq",
        input="Valid input prompt",
        output="Valid output response",
        supporting_context="Textbook context.",
        traceability=DatasetExampleTraceability(
            knowledge_unit_ids=[uuid.uuid4()],
            concept_ids=[uuid.uuid4()],
        ),
    )

    col = DatasetCollection(collection_id=uuid.uuid4(), examples=[ex1])
    warnings: list[str] = []

    assert struct_val.validate(col, warnings) is True
    assert edu_val.validate(col, warnings) is True
    assert len(warnings) == 0

    ex2 = DatasetExample(
        example_id=uuid.uuid4(),
        format_tag="mcq",
        input="   ",
        output="Response",
        supporting_context="",
        traceability=DatasetExampleTraceability(
            knowledge_unit_ids=[uuid.uuid4()],
            concept_ids=[uuid.uuid4()],
        ),
    )

    col_invalid_struct = DatasetCollection(collection_id=uuid.uuid4(), examples=[ex2])
    assert struct_val.validate(col_invalid_struct, warnings) is False
    assert len(warnings) > 0

    ex3 = DatasetExample(
        example_id=uuid.uuid4(),
        format_tag="tutor",
        input="Input",
        output="Response",
        supporting_context="",
        traceability=DatasetExampleTraceability(
            knowledge_unit_ids=[],
            concept_ids=[],
        ),
    )

    warnings.clear()
    col_invalid_edu = DatasetCollection(collection_id=uuid.uuid4(), examples=[ex3])
    assert edu_val.validate(col_invalid_edu, warnings) is False
    assert len(warnings) > 0
