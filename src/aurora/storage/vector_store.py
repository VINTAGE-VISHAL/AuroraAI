"""Persistent ChromaDB Vector Store Implementation for AuroraAI.

Provides:
- Persistent vector storage scoped per conversation using ChromaDB collections
- Reusable singleton / persistent client connection
- Strict vector validation: dimension consistency, finiteness checks (no NaNs or Infs)
- Full metadata preservation: chunk_id, file_id, conversation_id, filename, text,
  chunk_index, total_chunks, source_page, offsets, char_count, token_estimate
- Upsert semantics to prevent duplicate vectors when re-indexing
- File-level deletion and conversation-level collection cleanup
- Cross-conversation isolation
"""

import hashlib
import json
import logging
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from aurora.config.settings import VectorStoreConfig
from aurora.core.exceptions import (
    InvalidTopKError,
    MalformedVectorError,
    StorageOperationError,
    VectorDimensionMismatchError,
    VectorStoreError,
)
from aurora.interfaces.vector_store import IVectorStore
from aurora.models.embedding import EmbeddedChunk
from aurora.models.retrieval import ScoredChunk
from aurora.models.runtime_chunk import DocumentChunk
from aurora.models.vector_store import VectorRecord

logger = logging.getLogger(__name__)


class ChromaVectorStore(IVectorStore):
    """Production ChromaDB-backed persistent vector store implementation."""

    def __init__(
        self,
        config: Optional[VectorStoreConfig] = None,
        client: Optional[chromadb.api.ClientAPI] = None,
    ) -> None:
        self.config = config or VectorStoreConfig()
        self.persist_dir = Path(self.config.persist_dir).resolve()
        self.dimension = self.config.embedding_dimension
        self.distance_metric = self.config.distance_metric

        if client is not None:
            self._client = client
        else:
            try:
                self.persist_dir.mkdir(parents=True, exist_ok=True)
                self._client = chromadb.PersistentClient(
                    path=str(self.persist_dir),
                    settings=ChromaSettings(anonymized_telemetry=False),
                )
            except Exception as e:
                logger.error(f"Failed to initialize ChromaDB PersistentClient at {self.persist_dir}: {e}")
                raise VectorStoreError(f"Vector store database initialization failed: {e}") from e

    def _get_collection_name(self, conversation_id: str) -> str:
        """Derives a valid ChromaDB collection name from conversation_id.
        
        ChromaDB collection naming requirements:
        - 3-63 characters
        - Starts and ends with alphanumeric
        - Contains only alphanumeric, underscores, or hyphens
        """
        clean = re.sub(r"[^a-zA-Z0-9_\-]", "_", conversation_id.strip())
        name = f"conv_{clean}"
        if len(name) > 63:
            # Deterministic hash suffix to keep under 63 chars
            suffix = hashlib.sha256(conversation_id.encode("utf-8")).hexdigest()[:12]
            name = f"{name[:50]}_{suffix}"
        if len(name) < 3:
            name = f"conv_aurora_{clean}"
        return name

    def _get_or_create_collection(self, conversation_id: str) -> chromadb.api.models.Collection.Collection:
        """Gets or creates the Chroma collection for the given conversation."""
        coll_name = self._get_collection_name(conversation_id)
        space = "cosine" if self.distance_metric == "cosine" else ("l2" if self.distance_metric == "l2" else "ip")
        try:
            return self._client.get_or_create_collection(
                name=coll_name,
                metadata={"hnsw:space": space},
            )
        except Exception as e:
            logger.error(f"Failed to get/create ChromaDB collection '{coll_name}': {e}")
            raise VectorStoreError(f"Failed accessing collection for conversation '{conversation_id}': {e}") from e

    def _validate_vector(self, chunk: EmbeddedChunk) -> None:
        """Ensures vector dimension matches configuration and contains only finite numbers."""
        if len(chunk.embedding) != self.dimension:
            raise VectorDimensionMismatchError(
                f"Vector dimension mismatch for chunk '{chunk.chunk_id}': "
                f"expected {self.dimension}, got {len(chunk.embedding)}"
            )

        for i, val in enumerate(chunk.embedding):
            if not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
                raise MalformedVectorError(
                    f"Vector contains invalid float at index {i} in chunk '{chunk.chunk_id}': {val}"
                )

    def store_embedded_chunks(
        self,
        conversation_id: str,
        chunks: List[EmbeddedChunk],
    ) -> int:
        """Stores or upserts a batch of EmbeddedChunks into the conversation's vector collection."""
        if not conversation_id or not conversation_id.strip():
            raise VectorStoreError("conversation_id cannot be empty.")

        if not chunks:
            return 0

        # Validate all vectors before writing
        for chunk in chunks:
            self._validate_vector(chunk)

        collection = self._get_or_create_collection(conversation_id)

        ids: List[str] = []
        embeddings: List[List[float]] = []
        documents: List[str] = []
        metadatas: List[Dict[str, Any]] = []

        for c in chunks:
            ids.append(c.chunk_id)
            embeddings.append(c.embedding)
            documents.append(c.chunk.text)

            meta: Dict[str, Any] = {
                "chunk_id": c.chunk_id,
                "file_id": c.file_id,
                "conversation_id": conversation_id,
                "filename": c.chunk.filename,
                "chunk_index": c.chunk.chunk_index,
                "total_chunks": c.chunk.total_chunks,
                "has_source_page": c.chunk.source_page is not None,
                "source_page": c.chunk.source_page if c.chunk.source_page is not None else 0,
                "char_count": c.chunk.char_count,
                "token_estimate": c.chunk.token_estimate,
                "start_char": c.chunk.start_char if c.chunk.start_char is not None else -1,
                "end_char": c.chunk.end_char if c.chunk.end_char is not None else -1,
            }
            metadatas.append(meta)

        try:
            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
            return len(ids)
        except Exception as e:
            logger.error(f"Failed to upsert chunks into collection for conversation '{conversation_id}': {e}")
            raise StorageOperationError(f"Vector storage upsert operation failed: {e}") from e

    def get_chunk(
        self,
        conversation_id: str,
        chunk_id: str,
    ) -> Optional[VectorRecord]:
        """Retrieves a single stored vector record by chunk_id within a conversation scope."""
        if not conversation_id or not chunk_id:
            return None

        coll_name = self._get_collection_name(conversation_id)
        try:
            # Check if collection exists
            existing_names = [c.name for c in self._client.list_collections()]
            if coll_name not in existing_names:
                return None
            collection = self._client.get_collection(coll_name)
        except Exception:
            return None

        try:
            res = collection.get(
                ids=[chunk_id],
                include=["embeddings", "documents", "metadatas"],
            )
            if not res or not res["ids"] or len(res["ids"]) == 0:
                return None

            return self._record_from_chroma_item(
                chunk_id=res["ids"][0],
                embedding=res["embeddings"][0] if res.get("embeddings") is not None else [],
                document=res["documents"][0] if res.get("documents") is not None else "",
                metadata=res["metadatas"][0] if res.get("metadatas") is not None else {},
                conversation_id=conversation_id,
            )
        except Exception as e:
            logger.error(f"Error retrieving chunk '{chunk_id}' for conversation '{conversation_id}': {e}")
            raise StorageOperationError(f"Vector store retrieval failed: {e}") from e

    def get_file_chunks(
        self,
        conversation_id: str,
        file_id: str,
    ) -> List[VectorRecord]:
        """Retrieves all vector records belonging to a file within a conversation scope."""
        if not conversation_id or not file_id:
            return []

        coll_name = self._get_collection_name(conversation_id)
        try:
            existing_names = [c.name for c in self._client.list_collections()]
            if coll_name not in existing_names:
                return []
            collection = self._client.get_collection(coll_name)
        except Exception:
            return []

        try:
            res = collection.get(
                where={"file_id": file_id},
                include=["embeddings", "documents", "metadatas"],
            )
            records: List[VectorRecord] = []
            if not res or not res["ids"]:
                return records

            for i in range(len(res["ids"])):
                cid = res["ids"][i]
                emb = res["embeddings"][i] if res.get("embeddings") is not None else []
                doc = res["documents"][i] if res.get("documents") is not None else ""
                meta = res["metadatas"][i] if res.get("metadatas") is not None else {}
                records.append(
                    self._record_from_chroma_item(
                        chunk_id=cid,
                        embedding=emb,
                        document=doc,
                        metadata=meta,
                        conversation_id=conversation_id,
                    )
                )

            # Sort by chunk_index
            records.sort(key=lambda r: r.chunk.chunk_index)
            return records
        except Exception as e:
            logger.error(f"Error retrieving file chunks for file '{file_id}': {e}")
            raise StorageOperationError(f"Vector store retrieval failed: {e}") from e

    def count(self, conversation_id: str, file_id: Optional[str] = None) -> int:
        """Returns the total number of vectors in a conversation, optionally filtered by file_id."""
        if not conversation_id:
            return 0

        coll_name = self._get_collection_name(conversation_id)
        try:
            existing_names = [c.name for c in self._client.list_collections()]
            if coll_name not in existing_names:
                return 0
            collection = self._client.get_collection(coll_name)
        except Exception:
            return 0

        try:
            if file_id is not None:
                res = collection.get(where={"file_id": file_id})
                return len(res["ids"]) if res and res["ids"] else 0
            return collection.count()
        except Exception as e:
            logger.error(f"Error counting vectors in collection '{coll_name}': {e}")
            raise StorageOperationError(f"Vector store count operation failed: {e}") from e

    def delete_file(
        self,
        conversation_id: str,
        file_id: str,
    ) -> int:
        """Deletes all vectors associated with a file within a conversation scope."""
        if not conversation_id or not file_id:
            return 0

        coll_name = self._get_collection_name(conversation_id)
        try:
            existing_names = [c.name for c in self._client.list_collections()]
            if coll_name not in existing_names:
                return 0
            collection = self._client.get_collection(coll_name)
        except Exception:
            return 0

        try:
            # Check how many exist before deleting
            existing_res = collection.get(where={"file_id": file_id})
            count = len(existing_res["ids"]) if existing_res and existing_res["ids"] else 0
            if count > 0:
                collection.delete(where={"file_id": file_id})
            return count
        except Exception as e:
            logger.error(f"Error deleting file '{file_id}' from collection '{coll_name}': {e}")
            raise StorageOperationError(f"Vector store delete operation failed: {e}") from e

    def delete_conversation(
        self,
        conversation_id: str,
    ) -> bool:
        """Deletes the entire vector collection for a conversation."""
        if not conversation_id:
            return False

        coll_name = self._get_collection_name(conversation_id)
        try:
            existing_names = [c.name for c in self._client.list_collections()]
            if coll_name in existing_names:
                self._client.delete_collection(coll_name)
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting collection '{coll_name}': {e}")
            raise StorageOperationError(f"Vector store collection deletion failed: {e}") from e

    def query_vectors(
        self,
        conversation_id: str,
        query_vector: List[float],
        top_k: int = 5,
        file_id: Optional[str] = None,
    ) -> List[ScoredChunk]:
        """Queries the conversation's vector collection for the most similar chunks.
        
        Args:
            conversation_id: Conversation isolation scope identifier.
            query_vector: Dense query embedding vector.
            top_k: Maximum number of nearest neighbors to return (must be positive).
            file_id: Optional file filter within the conversation.
            
        Returns:
            Ranked list of ScoredChunks sorted by relevance score descending.
        """
        if not conversation_id or not conversation_id.strip():
            raise VectorStoreError("conversation_id cannot be empty.")

        if not isinstance(top_k, int) or top_k <= 0:
            raise InvalidTopKError(f"top_k must be a positive integer, got: {top_k}")

        if not query_vector:
            return []

        if len(query_vector) != self.dimension:
            raise VectorDimensionMismatchError(
                f"Query vector dimension mismatch: expected {self.dimension}, got {len(query_vector)}"
            )

        for i, val in enumerate(query_vector):
            if not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
                raise MalformedVectorError(f"Query vector contains invalid float at index {i}: {val}")

        coll_name = self._get_collection_name(conversation_id)
        try:
            existing_names = [c.name for c in self._client.list_collections()]
            if coll_name not in existing_names:
                return []
            collection = self._client.get_collection(coll_name)
        except Exception:
            return []

        coll_count = collection.count()
        if coll_count == 0:
            return []

        # Request at most the available chunks in collection
        n_results = min(top_k, coll_count)
        where_filter = {"file_id": file_id} if file_id else None

        try:
            res = collection.query(
                query_embeddings=[query_vector],
                n_results=n_results,
                where=where_filter,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.error(f"Error querying collection '{coll_name}': {e}")
            raise StorageOperationError(f"Vector store query failed: {e}") from e

        if not res or not res["ids"] or len(res["ids"][0]) == 0:
            return []

        scored_chunks: List[ScoredChunk] = []
        ids = res["ids"][0]
        docs = res["documents"][0] if res.get("documents") else [""] * len(ids)
        metas = res["metadatas"][0] if res.get("metadatas") else [{}] * len(ids)
        distances = res["distances"][0] if res.get("distances") else [0.0] * len(ids)

        for cid, doc, meta, dist in zip(ids, docs, metas, distances):
            # ChromaDB cosine distance d in [0, 2] -> cosine similarity s = 1.0 - d
            score = 1.0 - dist if self.distance_metric == "cosine" else -dist

            source_page = meta.get("source_page")
            if not meta.get("has_source_page", False) or source_page == 0:
                source_page = None

            start_char = meta.get("start_char")
            if start_char == -1:
                start_char = None

            end_char = meta.get("end_char")
            if end_char == -1:
                end_char = None

            doc_chunk = DocumentChunk(
                chunk_id=cid,
                file_id=str(meta.get("file_id", "")),
                filename=str(meta.get("filename", "")),
                text=doc,
                chunk_index=int(meta.get("chunk_index", 0)),
                total_chunks=int(meta.get("total_chunks", 1)),
                source_page=source_page,
                start_char=start_char,
                end_char=end_char,
                char_count=int(meta.get("char_count", len(doc))),
                token_estimate=int(meta.get("token_estimate", 0)),
            )

            scored_chunks.append(
                ScoredChunk(
                    chunk_id=cid,
                    file_id=str(meta.get("file_id", "")),
                    conversation_id=conversation_id,
                    score=float(score),
                    distance=float(dist),
                    chunk=doc_chunk,
                )
            )

        # Sort descending by score; for score ties, sort ascending by chunk_index
        scored_chunks.sort(key=lambda sc: (-sc.score, sc.chunk.chunk_index))
        return scored_chunks[:top_k]

    def _record_from_chroma_item(
        self,
        chunk_id: str,
        embedding: List[float],
        document: str,
        metadata: Dict[str, Any],
        conversation_id: str,
    ) -> VectorRecord:
        """Reconstructs a clean VectorRecord and DocumentChunk from ChromaDB storage items."""
        source_page = metadata.get("source_page")
        if not metadata.get("has_source_page", False) or source_page == 0:
            source_page = None

        start_char = metadata.get("start_char")
        if start_char == -1:
            start_char = None

        end_char = metadata.get("end_char")
        if end_char == -1:
            end_char = None

        doc_chunk = DocumentChunk(
            chunk_id=chunk_id,
            file_id=str(metadata.get("file_id", "")),
            filename=str(metadata.get("filename", "")),
            text=document,
            chunk_index=int(metadata.get("chunk_index", 0)),
            total_chunks=int(metadata.get("total_chunks", 1)),
            source_page=source_page,
            start_char=start_char,
            end_char=end_char,
            char_count=int(metadata.get("char_count", len(document))),
            token_estimate=int(metadata.get("token_estimate", 0)),
        )

        if embedding is not None:
            if hasattr(embedding, "tolist"):
                emb_list = embedding.tolist()
            else:
                emb_list = list(embedding)
        else:
            emb_list = []

        return VectorRecord(
            chunk_id=chunk_id,
            file_id=str(metadata.get("file_id", "")),
            conversation_id=conversation_id,
            embedding=emb_list,
            dimension=len(emb_list) if len(emb_list) > 0 else self.dimension,
            chunk=doc_chunk,
        )
