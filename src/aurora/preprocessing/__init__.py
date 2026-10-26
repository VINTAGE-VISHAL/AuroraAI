"""Preprocessing phase package."""

from typing import List

from aurora.config.settings import Settings
from aurora.interfaces.preprocessing import IPreprocessor
from aurora.models.document import ProcessedDocument, RawDocument
from aurora.registry.module_registry import ModuleRegistry


@ModuleRegistry.register("preprocessing")
class DefaultPreprocessor(IPreprocessor):
    """Default text preprocessing and chunking implementation."""

    def __init__(self, config: Settings) -> None:
        self.config = config

    def run(self, input_data: List[RawDocument]) -> List[ProcessedDocument]:
        processed_docs = []
        for i, doc in enumerate(input_data):
            # Temporarily decode bytes for the preprocessor implementation stub
            decoded_content = doc.content_bytes.decode("utf-8", errors="ignore")
            processed_docs.append(
                ProcessedDocument(
                    doc_id=f"doc_{i}",
                    parent_doc_id=doc.metadata.source_path,
                    chunk_index=0,
                    content=decoded_content.strip().lower(),
                    keywords=["mock", "educational"],
                    metadata=doc.metadata,
                )
            )
        return processed_docs



from aurora.preprocessing.runtime_chunker import RuntimeChunker

__all__ = [
    "DefaultPreprocessor",
    "RuntimeChunker",
]


