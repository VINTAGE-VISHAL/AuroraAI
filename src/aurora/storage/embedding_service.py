"""Runtime dense vector embedding service implementation using Sentence Transformers."""

import logging
import math
from typing import Any, List, Optional

import numpy as np

from aurora.config.settings import EmbeddingConfig
from aurora.core.exceptions import (
    EmbeddingError,
    EmbeddingInferenceError,
    ModelLoadError,
)
from aurora.interfaces.embedding import IEmbeddingService
from aurora.models.embedding import EmbeddedChunk, EmbeddingBatchResult
from aurora.models.runtime_chunk import DocumentChunk

logger = logging.getLogger(__name__)


class SentenceTransformerEmbeddingService(IEmbeddingService):
    """Production runtime dense vector embedding service.
    
    - Uses local SentenceTransformer models (default: sentence-transformers/all-MiniLM-L6-v2).
    - Implements lazy singleton model loading so models are cached across calls.
    - Normalizes embeddings (L2 unit vectors) suitable for cosine distance retrieval.
    - Supports device auto-detection with graceful CPU fallback.
    - Accepts batches of DocumentChunks and returns EmbeddedChunk records preserving metadata.
    """

    def __init__(
        self,
        config: Optional[EmbeddingConfig] = None,
        model_instance: Optional[Any] = None,
    ) -> None:
        self.config = config or EmbeddingConfig()
        self._model = model_instance
        self._device = self._resolve_device(self.config.device)
        self._dimension: Optional[int] = None

    def _resolve_device(self, configured_device: str) -> str:
        """Resolves target compute device based on configuration and hardware availability."""
        dev = (configured_device or "auto").lower().strip()
        if dev == "auto":
            try:
                import torch
                return "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                return "cpu"
        elif dev in ("cuda", "cpu"):
            return dev
        return "cpu"

    def _load_model(self) -> Any:
        """Lazily loads the SentenceTransformer model once and caches the instance."""
        if self._model is not None:
            return self._model

        model_name = self.config.model_name
        logger.info(f"Loading local SentenceTransformer model '{model_name}' on device '{self._device}'...")

        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(model_name, device=self._device)
            logger.info(f"SentenceTransformer '{model_name}' loaded successfully.")
            return self._model
        except Exception as e:
            logger.error(f"Failed to load embedding model '{model_name}': {e}")
            raise ModelLoadError(f"Failed to load embedding model '{model_name}': {e}") from e

    @property
    def dimension(self) -> int:
        """Returns dense vector dimension (e.g. 384 for all-MiniLM-L6-v2)."""
        if self._dimension is not None:
            return self._dimension

        # If model is already loaded and exposes dimension
        if self._model is not None:
            if hasattr(self._model, "get_sentence_embedding_dimension"):
                self._dimension = self._model.get_sentence_embedding_dimension()
                return self._dimension
            elif hasattr(self._model, "dimension"):
                self._dimension = self._model.dimension
                return self._dimension

        # Fallback to config default
        return self.config.embedding_dimension

    @property
    def model_name(self) -> str:
        return self.config.model_name

    @property
    def device(self) -> str:
        return self._device

    def _normalize_vector(self, vec: List[float]) -> List[float]:
        """Normalizes a 1D vector to unit L2 norm."""
        arr = np.array(vec, dtype=np.float32)
        norm = np.linalg.norm(arr)
        if norm > 1e-12:
            arr = arr / norm
        return [float(x) for x in arr]

    def embed_text(self, text: str) -> List[float]:
        """Generates a dense vector embedding for a single text query or string."""
        if not text or not text.strip():
            raise EmbeddingError("Cannot generate embedding for empty or whitespace-only text.")

        model = self._load_model()
        try:
            embedding = model.encode(
                text,
                normalize_embeddings=self.config.normalize_embeddings,
                show_progress_bar=False,
            )
            # Convert to list of python floats
            if hasattr(embedding, "tolist"):
                vec = embedding.tolist()
            else:
                vec = [float(x) for x in embedding]

            # Verify finite values
            if not all(math.isfinite(x) for x in vec):
                raise EmbeddingInferenceError("Embedding vector contains NaN or infinite numerical values.")

            if self._dimension is None:
                self._dimension = len(vec)

            return vec
        except Exception as e:
            if isinstance(e, EmbeddingError):
                raise
            raise EmbeddingInferenceError(f"Error generating embedding for text: {e}") from e

    def embed_chunks(self, chunks: List[DocumentChunk]) -> EmbeddingBatchResult:
        """Generates dense vector embeddings for an ordered sequence of DocumentChunks."""
        if not chunks:
            return EmbeddingBatchResult(
                model_name=self.model_name,
                dimension=self.dimension,
                embedded_chunks=[],
                total_chunks=0,
                normalized=self.config.normalize_embeddings,
            )

        texts = [chunk.text for chunk in chunks]
        # Validate that no chunk is empty
        for idx, t in enumerate(texts):
            if not t or not t.strip():
                raise EmbeddingError(f"DocumentChunk at index {idx} has empty text.")

        model = self._load_model()
        batch_size = max(1, self.config.batch_size)

        try:
            embeddings_arr = model.encode(
                texts,
                batch_size=batch_size,
                normalize_embeddings=self.config.normalize_embeddings,
                show_progress_bar=False,
            )

            embedded_chunks: List[EmbeddedChunk] = []
            for chunk, vec_arr in zip(chunks, embeddings_arr):
                vec = [float(x) for x in vec_arr]
                # Validate finite numerical values
                if not all(math.isfinite(x) for x in vec):
                    raise EmbeddingInferenceError(
                        f"Embedding for chunk '{chunk.chunk_id}' contains NaN or infinite values."
                    )

                if self._dimension is None:
                    self._dimension = len(vec)

                embedded_chunks.append(
                    EmbeddedChunk(
                        chunk_id=chunk.chunk_id,
                        file_id=chunk.file_id,
                        embedding=vec,
                        dimension=len(vec),
                        chunk=chunk,
                    )
                )

            return EmbeddingBatchResult(
                model_name=self.model_name,
                dimension=self.dimension,
                embedded_chunks=embedded_chunks,
                total_chunks=len(embedded_chunks),
                normalized=self.config.normalize_embeddings,
            )
        except Exception as e:
            if isinstance(e, EmbeddingError):
                raise
            raise EmbeddingInferenceError(f"Batch embedding generation failed: {e}") from e
