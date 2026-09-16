"""ZIP and open office format signature detector."""

import io
import zipfile
from typing import Optional

from aurora.core.pipeline import PipelineContext
from aurora.extraction.interfaces import IDocumentDetector
from aurora.extraction.models import DetectionMethod, DocumentDescriptor, DocumentType


class ZipDetector(IDocumentDetector):
    """Detects ZIP magic signature and sub-inspects DOCX, XLSX, PPTX, EPUB structures."""

    def process(self, input_data: bytes, context: PipelineContext) -> Optional[DocumentDescriptor]:
        if not input_data.startswith(b"PK\x03\x04"):
            return None

        try:
            with zipfile.ZipFile(io.BytesIO(input_data)) as zf:
                namelist = zf.namelist()
                if "word/document.xml" in namelist:
                    return DocumentDescriptor(
                        doc_type=DocumentType.DOCX,
                        confidence=1.0,
                        method=DetectionMethod.HEURISTIC,
                        signature="PK-word",
                    )
                if "xl/workbook.xml" in namelist:
                    return DocumentDescriptor(
                        doc_type=DocumentType.XLSX,
                        confidence=1.0,
                        method=DetectionMethod.HEURISTIC,
                        signature="PK-excel",
                    )
                if "ppt/presentation.xml" in namelist:
                    return DocumentDescriptor(
                        doc_type=DocumentType.PPTX,
                        confidence=1.0,
                        method=DetectionMethod.HEURISTIC,
                        signature="PK-powerpoint",
                    )
                if "META-INF/container.xml" in namelist:
                    return DocumentDescriptor(
                        doc_type=DocumentType.EPUB,
                        confidence=1.0,
                        method=DetectionMethod.HEURISTIC,
                        signature="PK-epub",
                    )
                return DocumentDescriptor(
                    doc_type=DocumentType.ZIP,
                    confidence=1.0,
                    method=DetectionMethod.MAGIC_BYTES,
                    signature="PK\x03\x04",
                )
        except zipfile.BadZipFile:
            return DocumentDescriptor(
                doc_type=DocumentType.UNKNOWN,
                confidence=0.1,
                method=DetectionMethod.FALLBACK,
                signature="PK-corrupt",
            )
