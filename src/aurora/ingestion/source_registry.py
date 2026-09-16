"""Source Registry implementation managing documents and tracking state changes."""

import hashlib
import time
from pathlib import Path
from typing import Dict, List
from urllib.parse import urlparse
from urllib.request import url2pathname

from aurora.core.exceptions import DuplicateSourceError, SourceNotFoundError
from aurora.interfaces.ingestion import IFileScanner, ISourceRegistry
from aurora.models.source import (
    DocumentChange,
    SourceDocument,
    SourceStatus,
)


class SourceRegistry(ISourceRegistry):
    """Canonical registry for tracked documents, computing stable IDs and state changes."""

    def __init__(self) -> None:
        self._documents: Dict[str, SourceDocument] = {}

    def _generate_stable_id(self, uri: str, checksum: str) -> str:
        """Generate a stable, deterministic ID from URI and checksum."""
        hasher = hashlib.sha256()
        hasher.update(f"{uri}:{checksum}".encode("utf-8"))
        return hasher.hexdigest()

    def _extract_subject(self, uri: str, root_uri: str) -> str:
        """Extract subject name based on relative path folder from root."""
        try:
            if not root_uri.startswith("file://") and "://" not in root_uri:
                path_root = Path(root_uri).resolve()
            else:
                parsed_root = urlparse(root_uri)
                path_root = Path(url2pathname(parsed_root.path)).resolve()

            parsed_uri = urlparse(uri)
            path_doc = Path(url2pathname(parsed_uri.path)).resolve()

            # Resolve relative parts
            relative = path_doc.relative_to(path_root)
            if len(relative.parts) > 1:
                return relative.parts[0]
        except Exception:
            pass
        return "default"


    def refresh(
        self, scanner: IFileScanner, root_uri: str, allowed_extensions: set[str]
    ) -> List[DocumentChange]:
        """Synchronizes filesystem scanned results with registry state."""
        scanned_metadata = scanner.scan(root_uri, allowed_extensions)
        changes: List[DocumentChange] = []

        # Track which URIs are found during this scan to detect removals
        scanned_uris = {m.uri for m in scanned_metadata}

        # 1. Process scanned files (New/Modified/Unchanged)
        for metadata in scanned_metadata:
            subject = self._extract_subject(metadata.uri, root_uri)

            # Find existing active document with the same URI
            existing_doc = None
            for doc in self._documents.values():
                if doc.uri == metadata.uri and doc.metadata.status != SourceStatus.REMOVED:
                    existing_doc = doc
                    break

            if existing_doc is None:
                # Document is NEW
                stable_id = self._generate_stable_id(metadata.uri, metadata.checksum)

                # Check for duplicate registration of identical IDs
                if stable_id in self._documents:
                    raise DuplicateSourceError(
                        f"A document with ID {stable_id} is already registered."
                    )

                metadata.status = SourceStatus.ACTIVE
                metadata.registered_at = time.time()
                metadata.last_verified = time.time()

                new_doc = SourceDocument(
                    doc_id=stable_id,
                    uri=metadata.uri,
                    checksum=metadata.checksum,
                    subject_name=subject,
                    metadata=metadata,
                )
                self._documents[stable_id] = new_doc
                changes.append(DocumentChange.NEW)
            else:
                # Document already registered. Check for modifications.
                if existing_doc.checksum != metadata.checksum:
                    # Document is MODIFIED
                    existing_doc.checksum = metadata.checksum

                    # Update metadata inline
                    existing_meta = existing_doc.metadata
                    existing_meta.checksum = metadata.checksum
                    existing_meta.size_bytes = metadata.size_bytes
                    existing_meta.version += 1
                    existing_meta.status = SourceStatus.MODIFIED
                    existing_meta.last_verified = time.time()

                    changes.append(DocumentChange.MODIFIED)
                else:
                    # Document is UNCHANGED
                    existing_doc.metadata.last_verified = time.time()
                    existing_doc.metadata.status = SourceStatus.ACTIVE
                    changes.append(DocumentChange.UNCHANGED)

        # 2. Process removals (Registered documents not found in scan)
        for doc in list(self._documents.values()):
            if doc.metadata.status != SourceStatus.REMOVED and doc.uri not in scanned_uris:
                doc.metadata.status = SourceStatus.REMOVED
                doc.metadata.last_verified = time.time()
                changes.append(DocumentChange.REMOVED)

        return changes

    def list_documents(self) -> List[SourceDocument]:
        """Return all active registered source documents."""
        return [
            doc for doc in self._documents.values()
            if doc.metadata.status != SourceStatus.REMOVED
        ]

    def get_document(self, doc_id: str) -> SourceDocument:
        """Retrieve a registered document by its stable identifier."""
        is_removed = (
            doc_id not in self._documents
            or self._documents[doc_id].metadata.status == SourceStatus.REMOVED
        )
        if is_removed:
            raise SourceNotFoundError(f"Document ID {doc_id} not found in registry.")
        return self._documents[doc_id]

    def get_documents_by_subject(self, subject_name: str) -> List[SourceDocument]:
        """Return all active documents associated with the subject."""
        return [
            doc for doc in self._documents.values()
            if doc.subject_name == subject_name and doc.metadata.status != SourceStatus.REMOVED
        ]

    def list_subjects(self) -> List[str]:
        """Return list of distinct subject names containing active documents."""
        subjects = {
            doc.subject_name for doc in self._documents.values()
            if doc.metadata.status != SourceStatus.REMOVED
        }
        return sorted(subjects)
