import hashlib
import os
import time
import uuid
from typing import Optional

from aurora.core.artifact import ArtifactMetadata
from aurora.core.exceptions import (
    ExtractionError,
    RuntimeFileNotFoundError,
    UnsupportedFileTypeError,
)
from aurora.extraction.plugins.docx import DOCXExtractor
from aurora.extraction.plugins.markdown import MarkdownExtractor
from aurora.extraction.plugins.pdf import PDFExtractor
from aurora.extraction.plugins.txt import TXTExtractor
from aurora.interfaces.context_fusion import IContextFusionService
from aurora.interfaces.embedding import IEmbeddingService
from aurora.interfaces.retriever import ISemanticRetriever
from aurora.interfaces.runtime_chunker import IRuntimeChunker
from aurora.interfaces.runtime_file import IFileService, IFileStorage, IFileValidator
from aurora.interfaces.vector_store import IVectorStore

from aurora.models import FrameworkInfo, PipelineProvenance, RawDocument
from aurora.models.context_fusion import FusedContext, GroundedPrompt
from aurora.models.embedding import EmbeddingBatchResult
from aurora.models.enums import DocumentState
from aurora.models.file_metadata import (
    CleanupResult,
    ExtractedFileResponse,
    FileStatus,
    RuntimeFileMetadata,
    RuntimeFileResponse,
)
from aurora.models.metadata import FileMetadata
from aurora.models.retrieval import RetrievalResult
from aurora.models.runtime_chunk import ChunkingConfig, ChunkingResult
from aurora.models.vector_store import IndexingResult, StoredChunkSummary
from aurora.preprocessing.runtime_chunker import RuntimeChunker
from aurora.storage.context_fusion import ContextFusionService
from aurora.storage.embedding_service import SentenceTransformerEmbeddingService
from aurora.storage.retriever import SemanticRetriever
from aurora.storage.vector_store import ChromaVectorStore


class FileService(IFileService):
    """Orchestrates runtime file upload, query, deletion, extraction, chunking, embedding, vector indexing, semantic retrieval, and context fusion."""

    def __init__(
        self,
        validator: IFileValidator,
        storage: IFileStorage,
        chunker: Optional[IRuntimeChunker] = None,
        embedding_service: Optional[IEmbeddingService] = None,
        vector_store: Optional[IVectorStore] = None,
        retriever: Optional[ISemanticRetriever] = None,
        context_fusion_service: Optional[IContextFusionService] = None,
    ) -> None:
        self.validator = validator
        self.storage = storage
        self.chunker = chunker or RuntimeChunker()
        self.embedding_service = embedding_service or SentenceTransformerEmbeddingService()
        self.vector_store = vector_store or ChromaVectorStore()
        self.retriever = retriever or SemanticRetriever(
            embedding_service=self.embedding_service,
            vector_store=self.vector_store,
        )
        self.context_fusion_service = context_fusion_service or ContextFusionService()
        self._extractors = {
            ".pdf": PDFExtractor(),
            ".docx": DOCXExtractor(),
            ".txt": TXTExtractor(),
            ".md": MarkdownExtractor(),
        }



    def upload_file(
        self,
        conversation_id: str,
        filename: str,
        content_type: Optional[str],
        content: bytes,
    ) -> RuntimeFileResponse:
        """Coordinates:
        1. Validation (filename, size, MIME, conversation_id)
        2. Binary stream header validation
        3. Unique file ID generation
        4. Storage persistence
        5. Metadata record creation
        """
        size_bytes = len(content)

        # 1. Validate high-level properties
        self.validator.validate(
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            conversation_id=conversation_id,
        )

        _, ext = os.path.splitext(filename)
        ext_lower = ext.lower()

        # 2. Binary header validation for binary formats (e.g. %PDF-, DOCX ZIP header)
        if size_bytes > 0:
            header_sample = content[:16]
            self.validator.validate_stream_header(header_sample, ext_lower)

        # 3. Generate secure unique file ID
        file_id = f"file_{uuid.uuid4().hex[:12]}"

        # 4. Save file to conversation storage
        storage_path = self.storage.save_file(
            conversation_id=conversation_id,
            file_id=file_id,
            original_filename=filename,
            content=content,
        )

        # 5. Build and save metadata
        metadata = RuntimeFileMetadata(
            file_id=file_id,
            conversation_id=conversation_id,
            filename=os.path.basename(filename.strip()),
            content_type=content_type or "application/octet-stream",
            size_bytes=size_bytes,
            extension=ext_lower,
            status=FileStatus.STORED,
            created_at=time.time(),
            storage_path=storage_path,
        )
        self.storage.save_metadata(metadata)

        # 6. Return client-safe DTO
        return RuntimeFileResponse.from_metadata(metadata)

    def get_file(
        self,
        file_id: str,
        conversation_id: Optional[str] = None,
    ) -> RuntimeFileResponse:
        """Retrieves file metadata without exposing filesystem paths."""
        meta = self.storage.get_metadata(file_id, conversation_id)
        if not meta:
            raise RuntimeFileNotFoundError(f"File '{file_id}' was not found.")
        return RuntimeFileResponse.from_metadata(meta)

    def delete_file(
        self,
        file_id: str,
        conversation_id: Optional[str] = None,
    ) -> bool:
        """Deletes file, metadata, and associated indexed vectors safely."""
        meta = self.storage.get_metadata(file_id, conversation_id)
        if not meta:
            raise RuntimeFileNotFoundError(f"File '{file_id}' was not found.")

        # Clean up vector database entries for this file
        conv_id = meta.conversation_id
        try:
            self.vector_store.delete_file(conv_id, file_id)
        except Exception:
            # Vector cleanup should be best effort if storage is being purged
            pass

        deleted = self.storage.delete_file(file_id, conversation_id)
        if not deleted:
            raise RuntimeFileNotFoundError(f"File '{file_id}' was not found.")
        return True

    def delete_conversation(self, conversation_id: str) -> bool:
        """Deletes all files, metadata, and the ChromaDB vector collection for a conversation."""
        if not conversation_id or not conversation_id.strip():
            return False

        # 1. Clean up vector collection
        try:
            self.vector_store.delete_conversation(conversation_id)
        except Exception:
            pass

        # 2. Clean up storage files and directory
        try:
            return self.storage.delete_conversation(conversation_id)
        except Exception:
            return False

    def cleanup_stale_files(
        self,
        max_age_hours: Optional[float] = None,
        active_conversation_ids: Optional[set[str]] = None,
    ) -> CleanupResult:
        """Executes safe, conservative cleanup of genuinely stale/abandoned runtime files.
        
        Safeguards:
        - Files younger than max_age_hours are strictly preserved.
        - Files belonging to active_conversation_ids are strictly preserved regardless of age.
        - Files currently in PROCESSING or UPLOADING states are strictly skipped.
        - Vector store entries and filesystem files are cleaned consistently.
        - Deletions are idempotent and logged without exposing document contents.
        """
        age_threshold_hours = max_age_hours if max_age_hours is not None else 24.0
        now = time.time()
        cutoff_timestamp = now - (age_threshold_hours * 3600.0)

        result = CleanupResult()
        scanned_convs: set[str] = set()

        try:
            all_meta = self.storage.list_all_metadata()
        except Exception as e:
            result.errors.append(f"Failed to list metadata: {e}")
            return result

        for meta in all_meta:
            scanned_convs.add(meta.conversation_id)

            # Safeguard 1: Active conversation preservation
            if active_conversation_ids and meta.conversation_id in active_conversation_ids:
                result.skipped_in_use_count += 1
                continue

            # Safeguard 2: In-flight operations preservation (PROCESSING or UPLOADING)
            if meta.status in (FileStatus.PROCESSING, FileStatus.UPLOADING):
                result.skipped_in_use_count += 1
                continue

            # Safeguard 3: Retention threshold check
            if meta.created_at >= cutoff_timestamp:
                result.skipped_in_use_count += 1
                continue

            # File is eligible for stale cleanup
            try:
                # 1. Purge vectors
                vec_count = 0
                try:
                    vec_count = self.vector_store.delete_file(meta.conversation_id, meta.file_id)
                except Exception:
                    pass

                # 2. Purge file storage & metadata
                storage_deleted = self.storage.delete_file(meta.file_id, meta.conversation_id)
                if storage_deleted:
                    result.cleaned_files_count += 1
                    result.cleaned_vectors_count += vec_count
                    result.stale_files.append(meta.file_id)
            except Exception as e:
                result.errors.append(f"Failed cleaning file '{meta.file_id}': {e}")

        result.scanned_conversations_count = len(scanned_convs)
        return result

    def extract_file(
        self,
        file_id: str,
        conversation_id: Optional[str] = None,
    ) -> ExtractedFileResponse:
        """Coordinates runtime document text extraction for a stored file.
        
        1. Validates file existence and conversation scope
        2. Retrieves content bytes from isolated storage
        3. Invokes format-specific extractor (PDF, DOCX, TXT, MD)
        4. Updates status in stored metadata (PROCESSING -> READY or FAILED)
        5. Returns structured extraction response with text, page count, and boundaries
        """
        meta = self.storage.get_metadata(file_id, conversation_id)
        if not meta:
            raise RuntimeFileNotFoundError(
                f"File '{file_id}' was not found"
                + (f" for conversation '{conversation_id}'." if conversation_id else ".")
            )

        ext = meta.extension.lower()
        if ext not in self._extractors:
            raise UnsupportedFileTypeError(f"No runtime extractor registered for extension '{ext}'.")

        extractor = self._extractors[ext]

        # Read binary content from storage
        content_bytes = self.storage.read_file(file_id, meta.conversation_id)
        content_hash = hashlib.sha256(content_bytes).hexdigest()

        # Build RawDocument bridge model
        raw_doc = RawDocument(
            doc_id=file_id,
            source_id=meta.conversation_id,
            uri=f"runtime://{meta.conversation_id}/{file_id}/{meta.filename}",
            content_bytes=content_bytes,
            content_hash=content_hash,
            state=DocumentState.LOADED,
            metadata=FileMetadata(
                source_path=meta.storage_path,
                file_type=ext.lstrip("."),
                char_count=len(content_bytes),
                custom_metadata={"original_filename": meta.filename},
            ),
            provenance=PipelineProvenance(
                stage=DocumentState.LOADED,
                producer="FileService",
                timestamp=time.time(),
                framework=FrameworkInfo(module_name="FileService", module_version="0.1.0"),
            ),
            artifact=ArtifactMetadata(
                artifact_id=uuid.uuid4(),
                checksum=content_hash,
                created_at=time.time(),
            ),
        )

        try:
            extracted_doc = extractor.extract(raw_doc)
            
            # Update stored status to READY
            updated_meta = meta.model_copy(update={"status": FileStatus.READY})
            self.storage.save_metadata(updated_meta)

            pages = extracted_doc.metadata.custom_metadata.get("pages", [])
            page_count = extracted_doc.metadata.custom_metadata.get("page_count", len(pages) if pages else (1 if extracted_doc.text else 0))

            return ExtractedFileResponse(
                file_id=file_id,
                conversation_id=meta.conversation_id,
                filename=meta.filename,
                extension=meta.extension,
                status=FileStatus.READY.value,
                text=extracted_doc.text,
                char_count=len(extracted_doc.text),
                page_count=page_count,
                pages=pages,
                has_content=bool(extracted_doc.text.strip()),
            )
        except Exception as e:
            # Mark status as FAILED in stored metadata
            updated_meta = meta.model_copy(update={"status": FileStatus.FAILED})
            self.storage.save_metadata(updated_meta)
            raise

    def chunk_file(
        self,
        file_id: str,
        conversation_id: Optional[str] = None,
        config: Optional[ChunkingConfig] = None,
    ) -> ChunkingResult:
        """Coordinates runtime text preprocessing and chunking for a stored/extracted file.
        
        Uses Module 02 extract_file as the single source of truth for extracted text,
        then invokes RuntimeChunker to produce deterministic, attribution-preserving DocumentChunks.
        """
        extracted = self.extract_file(file_id, conversation_id=conversation_id)
        return self.chunker.chunk_extracted_document(extracted, config=config)

    def embed_file(
        self,
        file_id: str,
        conversation_id: Optional[str] = None,
        config: Optional[ChunkingConfig] = None,
    ) -> EmbeddingBatchResult:
        """Coordinates runtime extraction, chunking, and dense vector embedding generation for a stored file.
        
        1. Calls chunk_file() which validates file/conversation ownership and extracts/chunks text.
        2. Passes DocumentChunks to the embedding service.
        3. Returns EmbeddingBatchResult containing dense vector representations for downstream Module 05.
        """
        chunk_result = self.chunk_file(file_id, conversation_id=conversation_id, config=config)
        return self.embedding_service.embed_chunks(chunk_result.chunks)

    def index_file(
        self,
        file_id: str,
        conversation_id: Optional[str] = None,
        config: Optional[ChunkingConfig] = None,
    ) -> IndexingResult:
        """Coordinates the end-to-end processing pipeline:
        Upload (prior) -> Extract -> Chunk -> Embed -> Store in vector database.
        
        1. Calls embed_file() to retrieve dense vector embeddings and chunk metadata.
        2. Resolves actual conversation_id from file metadata.
        3. Stores/upserts the embedded vectors into the persistent vector database.
        4. Returns IndexingResult detailing stored vectors and chunk summaries.
        """
        meta = self.storage.get_metadata(file_id, conversation_id)
        if not meta:
            raise RuntimeFileNotFoundError(
                f"File '{file_id}' was not found"
                + (f" for conversation '{conversation_id}'." if conversation_id else ".")
            )

        resolved_conv_id = meta.conversation_id
        embedding_result = self.embed_file(file_id, conversation_id=resolved_conv_id, config=config)

        # Store embedded chunks into the persistent vector store
        indexed_count = self.vector_store.store_embedded_chunks(
            conversation_id=resolved_conv_id,
            chunks=embedding_result.embedded_chunks,
        )

        summaries = [
            StoredChunkSummary(
                chunk_id=ec.chunk_id,
                file_id=ec.file_id,
                filename=ec.chunk.filename,
                chunk_index=ec.chunk.chunk_index,
                source_page=ec.chunk.source_page,
                char_count=ec.chunk.char_count,
            )
            for ec in embedding_result.embedded_chunks
        ]

        return IndexingResult(
            file_id=file_id,
            conversation_id=resolved_conv_id,
            indexed_count=indexed_count,
            dimension=embedding_result.dimension,
            chunks=summaries,
            success=True,
        )

    def retrieve_context(
        self,
        query: str,
        conversation_id: str,
        top_k: Optional[int] = None,
        file_id: Optional[str] = None,
    ) -> RetrievalResult:
        """Coordinates semantic retrieval of top-k relevant document chunks for Module 07 prompt context fusion."""
        return self.retriever.retrieve(
            query=query,
            conversation_id=conversation_id,
            top_k=top_k,
            file_id=file_id,
        )

    def build_rag_context(
        self,
        query: str,
        conversation_id: str,
        top_k: Optional[int] = None,
        file_id: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> FusedContext:
        """Retrieves and fuses document chunks into a structured, budget-bounded context."""
        retrieval_res = self.retrieve_context(
            query=query,
            conversation_id=conversation_id,
            top_k=top_k,
            file_id=file_id,
        )
        return self.context_fusion_service.fuse_context(
            query=query,
            chunks=retrieval_res.results,
            conversation_id=conversation_id,
            max_tokens=max_tokens,
        )

    def assemble_grounded_prompt(
        self,
        query: str,
        conversation_id: str,
        top_k: Optional[int] = None,
        file_id: Optional[str] = None,
        max_tokens: Optional[int] = None,
        base_system_prompt: Optional[str] = None,
    ) -> GroundedPrompt:
        """Retrieves, fuses, and assembles a grounded prompt ready for LLM consumption in Module 08."""
        fused = self.build_rag_context(
            query=query,
            conversation_id=conversation_id,
            top_k=top_k,
            file_id=file_id,
            max_tokens=max_tokens,
        )
        return self.context_fusion_service.assemble_grounded_prompt(
            query=query,
            fused_context=fused,
            base_system_prompt=base_system_prompt,
        )



