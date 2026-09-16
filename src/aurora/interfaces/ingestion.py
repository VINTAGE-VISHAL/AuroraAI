from abc import ABC, abstractmethod
from typing import List

from aurora.interfaces.base import IPipelineComponent
from aurora.models.document import RawDocument, ExtractedDocument
from aurora.models.source import DocumentChange, SourceDocument, SourceMetadata


class IIngestionService(IPipelineComponent[str, List[RawDocument]]):
    """Contract for consuming resources (e.g. PDFs, URLs) and outputting raw documents."""

    @abstractmethod
    def run(self, input_data: str) -> List[RawDocument]:
        """Ingests raw resources from a given source URI/path."""
        pass


class IFileScanner(ABC):
    """Contract for traversing paths and discovering educational resource files."""

    @abstractmethod
    def scan(self, root_uri: str, allowed_extensions: set[str]) -> List[SourceMetadata]:
        """Scans the given root URI recursively and gathers source metadata details."""
        pass


class ISourceRegistry(ABC):
    """Single source of truth contract for tracking and querying source document assets."""

    @abstractmethod
    def refresh(
        self, scanner: IFileScanner, root_uri: str, allowed_extensions: set[str]
    ) -> List[DocumentChange]:
        """Syncs filesystem assets, detects new/modified/removed state, updates registry."""
        pass


    @abstractmethod
    def list_documents(self) -> List[SourceDocument]:
        """Returns all currently active registered source documents."""
        pass

    @abstractmethod
    def get_document(self, doc_id: str) -> SourceDocument:
        """Retrieves a single document by its stable identifier."""
        pass

    @abstractmethod
    def get_documents_by_subject(self, subject_name: str) -> List[SourceDocument]:
        """Returns all documents associated with a specific subject."""
        pass

    @abstractmethod
    def list_subjects(self) -> List[str]:
        """Returns a list of all subjects discovered and registered."""
        pass


class IPDFExtractor(ABC):
    """Interface for extracting text from PDF source documents page by page."""

    @abstractmethod
    def extract(self, raw_doc: RawDocument) -> ExtractedDocument:
        """Extracts text contents from each page of the target RawDocument.

        Raises:
            InterfaceError: If the PDF is encrypted, corrupted, or unreadable.
        """
        pass


