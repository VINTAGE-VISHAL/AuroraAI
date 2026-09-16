from typing import List

from aurora.config.settings import Settings
from aurora.core.metrics import MetricsCollector
from aurora.ingestion.document_loader import DocumentLoader
from aurora.ingestion.file_scanner import FileScanner
from aurora.ingestion.source_registry import SourceRegistry
from aurora.ingestion.pdf_extractor import PDFExtractor
from aurora.interfaces.ingestion import IIngestionService
from aurora.models.document import RawDocument
from aurora.registry.module_registry import ModuleRegistry

__all__ = [
    "DefaultIngestionService",
    "FileScanner",
    "SourceRegistry",
    "DocumentLoader",
    "PDFExtractor",
]


@ModuleRegistry.register("ingestion")
class DefaultIngestionService(IIngestionService):
    """Default local file and folder ingestion service."""

    def __init__(self, config: Settings) -> None:
        self.config = config
        self.scanner = FileScanner()
        self.registry = SourceRegistry()
        self.metrics = MetricsCollector()
        self.loader = DocumentLoader(self.metrics)

    def run(self, input_data: str) -> List[RawDocument]:
        allowed_extensions = {".txt", ".pdf", ".md"}
        self.registry.refresh(self.scanner, input_data, allowed_extensions)

        raw_docs = []
        for doc in self.registry.list_documents():
            raw_doc = self.loader.load(doc)
            raw_docs.append(raw_doc)
        return raw_docs

