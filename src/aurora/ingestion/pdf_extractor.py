"""PDFExtractor component for Phase A raw text extraction."""

from datetime import datetime, timezone
from typing import List

import fitz  # PyMuPDF

from aurora.core.exceptions import InterfaceError
from aurora.interfaces.ingestion import IPDFExtractor
from aurora.models import DocumentState, ExtractedDocument, FileMetadata, PipelineProvenance, RawDocument
from aurora.models.provenance import FrameworkInfo
from aurora.registry.module_registry import ModuleRegistry


@ModuleRegistry.register("pdf_extractor")
class PDFExtractor(IPDFExtractor):
    """Responsible for extracting raw, unmodified text from loaded in-memory RawDocuments page-by-page."""

    def extract(self, raw_doc: RawDocument) -> ExtractedDocument:
        """Parses and extracts text from each page in reading order from raw document bytes."""
        if not raw_doc.content_bytes:
            raise InterfaceError(f"PDF extraction failed: Content bytes are empty for document '{raw_doc.doc_id}'")

        try:
            # Safely open PDF in-memory stream using the recommended context manager
            with fitz.open(stream=raw_doc.content_bytes, filetype="pdf") as doc:
                if doc.is_encrypted:
                    raise InterfaceError(f"PDF extraction failed: Document '{raw_doc.doc_id}' is encrypted.")

                pages_text: List[str] = []
                try:
                    for page_num in range(len(doc)):
                        page = doc.load_page(page_num)
                        # Extract text exactly as read; preserves empty strings for blank pages
                        text = page.get_text()
                        pages_text.append(text)
                except Exception as e:
                    raise InterfaceError(f"PDF extraction failed during page parsing for '{raw_doc.doc_id}': {e}")
        except Exception as e:
            if isinstance(e, InterfaceError):
                raise
            raise InterfaceError(f"PDF extraction failed: Cannot open or load corrupted PDF data: {e}")

        # Construct file metadata updating the char count
        char_count = sum(len(p) for p in pages_text)
        custom_metadata = dict(raw_doc.metadata.custom_metadata)
        custom_metadata.update({
            "page_count": len(pages_text),
            "sha256_checksum": raw_doc.content_hash,
        })
        meta = FileMetadata(
            source_path=raw_doc.metadata.source_path,
            file_type="pdf",
            char_count=char_count,
            custom_metadata=custom_metadata,
        )

        # Build pipeline execution provenance
        provenance = PipelineProvenance(
            stage=DocumentState.EXTRACTED,
            producer="PDFExtractor",
            timestamp=datetime.now(timezone.utc),
            framework=FrameworkInfo(
                framework_name="AuroraEngine",
                framework_version="0.1.0",
                module_name="pdf_extractor",
                module_version="0.1.0",
            ),
        )

        # Build artifact metadata
        import uuid
        from aurora.core.artifact import ArtifactMetadata
        artifact = ArtifactMetadata(
            artifact_id=uuid.uuid4(),
            parent_artifact_ids=[raw_doc.artifact.artifact_id] if raw_doc.artifact else [],
            derived_from=[raw_doc.artifact.artifact_id] if raw_doc.artifact else [],
            checksum=raw_doc.content_hash,
            created_at=provenance.timestamp,
        )

        return ExtractedDocument(
            doc_id=raw_doc.content_hash,
            uri=raw_doc.uri,
            pages=pages_text,
            metadata=meta,
            provenance=provenance,
            artifact=artifact,
        )
