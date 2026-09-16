"""Unit tests for Dataset Studio exporters."""

import json
import uuid

from aurora.models import (
    DatasetCollection,
    DatasetExample,
    DatasetExampleTraceability,
)
from aurora.studio.exporters import (
    AlpacaExporter,
    ChatMLExporter,
    JsonlExporter,
    ShareGPTExporter,
)


def test_exporters() -> None:
    """Verify JSONL, ChatML, ShareGPT, and Alpaca exporters formatting properties."""
    ex = DatasetExample(
        example_id=uuid.uuid4(),
        format_tag="tutor",
        input="Prompt text",
        output="Response text",
        supporting_context="Supporting text.",
        traceability=DatasetExampleTraceability(
            knowledge_unit_ids=[uuid.uuid4()],
            concept_ids=[uuid.uuid4()],
        ),
    )

    col = DatasetCollection(collection_id=uuid.uuid4(), examples=[ex])

    # 1. JSONL Export
    jsonl_output = JsonlExporter().export(col)
    assert jsonl_output.startswith("{")
    assert "Prompt text" in jsonl_output

    # 2. ChatML Export
    chatml_output = ChatMLExporter().export(col)
    chatml_data = json.loads(chatml_output)
    assert len(chatml_data) == 1
    assert chatml_data[0]["messages"][0]["role"] == "user"

    # 3. ShareGPT Export
    sharegpt_output = ShareGPTExporter().export(col)
    sharegpt_data = json.loads(sharegpt_output)
    assert len(sharegpt_data) == 1
    assert sharegpt_data[0]["conversations"][0]["from"] == "human"

    # 4. Alpaca Export
    alpaca_output = AlpacaExporter().export(col)
    alpaca_data = json.loads(alpaca_output)
    assert len(alpaca_data) == 1
    assert alpaca_data[0]["instruction"] == "Prompt text"
    assert alpaca_data[0]["input"] == "Supporting text."
