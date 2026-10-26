"""PDF document extractor plugin."""

from datetime import datetime, timezone
import hashlib
import uuid
import fitz  # PyMuPDF

from aurora.core.artifact import ArtifactMetadata
from aurora.core.exceptions import (
    CorruptedDocumentError,
    ExtractionFailedError,
    InterfaceError,
)
from aurora.extraction.interfaces import IDocumentExtractor
from aurora.extraction.models import (
    DocumentType,
    ExtractedDocument,
    ExtractorCapability,
    ExtractorMetadata,
)
from aurora.models import FrameworkInfo, PipelineProvenance, RawDocument
from aurora.models.enums import DocumentState
from aurora.models.metadata import FileMetadata


class PDFExtractor(IDocumentExtractor):
    """Production PDF document extractor utilizing PyMuPDF (fitz)."""

    def extract(self, doc: RawDocument) -> ExtractedDocument:
        content_bytes = doc.content_bytes
        if not content_bytes:
            # Empty file handled gracefully
            return self._build_empty_result(doc)

        try:
            with fitz.open(stream=content_bytes, filetype="pdf") as pdf_doc:
                if pdf_doc.is_encrypted:
                    raise ExtractionFailedError(
                        f"PDF extraction failed: Document '{doc.doc_id}' is password-protected or encrypted."
                    )

                pages_text: list[str] = []
                for page_idx in range(len(pdf_doc)):
                    try:
                        page = pdf_doc.load_page(page_idx)
                        page_text = page.get_text() or ""
                        pages_text.append(page_text)
                    except Exception as e:
                        raise CorruptedDocumentError(
                            f"Failed parsing page {page_idx + 1} of PDF '{doc.doc_id}': {e}"
                        ) from e

        except (ExtractionFailedError, CorruptedDocumentError):
            raise
        except Exception as e:
            raise CorruptedDocumentError(
                f"Failed to open or parse corrupted PDF data for '{doc.doc_id}': {e}"
            ) from e

        full_text = "\n\n".join(p.strip() for p in pages_text if p.strip()).strip()

        # Update metadata with page count and page texts
        custom_metadata = dict(doc.metadata.custom_metadata)
        custom_metadata.update({
            "page_count": len(pages_text),
            "pages": pages_text,
            "sha256_checksum": doc.content_hash,
        })

        meta = FileMetadata(
            source_path=doc.metadata.source_path,
            file_type="pdf",
            char_count=len(full_text),
            custom_metadata=custom_metadata,
            author=doc.metadata.author,
            created_at=doc.metadata.created_at,
        )

        provenance = PipelineProvenance(
            stage=DocumentState.EXTRACTED,
            producer="PDFExtractor",
            timestamp=datetime.now(timezone.utc),
            framework=FrameworkInfo(
                module_name="PDFExtractor",
                module_version="0.1.0",
            ),
            run_id=doc.provenance.run_id,
            execution_id=doc.provenance.execution_id,
        )

        content_hash = hashlib.sha256(full_text.encode("utf-8")).hexdigest()
        parent_ids = [doc.artifact.artifact_id] if doc.artifact else []
        artifact = ArtifactMetadata(
            artifact_id=uuid.uuid4(),
            parent_artifact_ids=parent_ids,
            derived_from=parent_ids,
            checksum=content_hash,
            created_at=provenance.timestamp,
            schema_version="1.0.0",
        )

        return ExtractedDocument(
            doc_id=doc.doc_id,
            text=full_text,
            tables=[],
            images=[],
            links=[],
            metadata=meta,
            provenance=provenance,
            artifact=artifact,
        )

    def _build_empty_result(self, doc: RawDocument) -> ExtractedDocument:
        custom_metadata = dict(doc.metadata.custom_metadata)
        custom_metadata.update({
            "page_count": 0,
            "pages": [],
            "sha256_checksum": doc.content_hash,
        })
        meta = FileMetadata(
            source_path=doc.metadata.source_path,
            file_type="pdf",
            char_count=0,
            custom_metadata=custom_metadata,
        )
        provenance = PipelineProvenance(
            stage=DocumentState.EXTRACTED,
            producer="PDFExtractor",
            timestamp=datetime.now(timezone.utc),
            framework=FrameworkInfo(module_name="PDFExtractor", module_version="0.1.0"),
        )
        parent_ids = [doc.artifact.artifact_id] if doc.artifact else []
        artifact = ArtifactMetadata(
            artifact_id=uuid.uuid4(),
            parent_artifact_ids=parent_ids,
            derived_from=parent_ids,
            checksum=doc.content_hash,
            created_at=provenance.timestamp,
        )
        return ExtractedDocument(
            doc_id=doc.doc_id,
            text="",
            tables=[],
            images=[],
            links=[],
            metadata=meta,
            provenance=provenance,
            artifact=artifact,
        )

    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            supported_type=DocumentType.PDF,
            version="0.1.0",
            capabilities={ExtractorCapability.TEXT, ExtractorCapability.METADATA},
        )

