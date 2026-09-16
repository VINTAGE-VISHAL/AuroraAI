"""Exporters converting DatasetCollection outputs to ChatML, ShareGPT, and Alpaca formats."""

import json

from aurora.models import DatasetCollection


class JsonlExporter:
    """Exporter for exporting datasets to raw JSONL string lines."""

    def export(self, collection: DatasetCollection) -> str:
        lines = []
        for ex in collection.examples:
            data = {
                "id": str(ex.example_id),
                "format": ex.format_tag,
                "prompt": ex.input,
                "response": ex.output,
                "context": ex.supporting_context,
            }
            lines.append(json.dumps(data))
        return "\n".join(lines)


class ChatMLExporter:
    """Exporter converting examples to ChatML message lists format."""

    def export(self, collection: DatasetCollection) -> str:
        exported = []
        for ex in collection.examples:
            messages = [
                {"role": "user", "content": ex.input},
                {"role": "assistant", "content": ex.output},
            ]
            exported.append({"messages": messages})
        return json.dumps(exported, indent=2)


class ShareGPTExporter:
    """Exporter converting examples to ShareGPT conversation lists format."""

    def export(self, collection: DatasetCollection) -> str:
        exported = []
        for ex in collection.examples:
            conversations = [
                {"from": "human", "value": ex.input},
                {"from": "gpt", "value": ex.output},
            ]
            exported.append({"conversations": conversations})
        return json.dumps(exported, indent=2)


class AlpacaExporter:
    """Exporter converting examples to Alpaca instruction format."""

    def export(self, collection: DatasetCollection) -> str:
        exported = []
        for ex in collection.examples:
            item = {
                "instruction": ex.input,
                "input": ex.supporting_context,
                "output": ex.output,
            }
            exported.append(item)
        return json.dumps(exported, indent=2)
