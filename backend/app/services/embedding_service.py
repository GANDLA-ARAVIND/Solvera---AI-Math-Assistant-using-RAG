"""Embedding service using SentenceTransformers for semantic vector representations."""

import logging
from sentence_transformers import SentenceTransformer
import numpy as np

logger = logging.getLogger(__name__)

# Default model — compact, fast, good quality for math/science text
DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"


class EmbeddingService:
    """Manages a SentenceTransformer model for encoding text into dense vectors."""

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME):
        self.model_name = model_name
        self._model: SentenceTransformer | None = None

    # ------------------------------------------------------------------
    # Lazy-load so the heavy model is only downloaded / loaded on first use
    # ------------------------------------------------------------------
    def _load_model(self) -> SentenceTransformer:
        if self._model is None:
            logger.info("Loading SentenceTransformer model '%s' …", self.model_name)
            self._model = SentenceTransformer(self.model_name)
            logger.info(
                "Model loaded. Embedding dimension: %d", self.get_dimension()
            )
        return self._model

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def encode(
        self,
        texts: list[str],
        batch_size: int = 64,
        show_progress: bool = False,
        normalize: bool = True,
    ) -> np.ndarray:
        """Encode a list of strings into a 2-D float32 numpy array.

        Args:
            texts: The texts to encode.
            batch_size: Batch size for the model (tune for your GPU / RAM).
            show_progress: Whether to show a tqdm progress bar.
            normalize: L2-normalize vectors (recommended for cosine similarity).

        Returns:
            np.ndarray of shape ``(len(texts), dim)`` with dtype float32.
        """
        if not texts:
            dim = self.get_dimension()
            return np.empty((0, dim), dtype=np.float32)

        model = self._load_model()
        embeddings = model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
            normalize_embeddings=normalize,
        )
        return embeddings.astype(np.float32)

    def encode_query(self, query: str, normalize: bool = True) -> np.ndarray:
        """Encode a single query string. Returns shape ``(1, dim)``."""
        return self.encode([query], normalize=normalize)

    def get_dimension(self) -> int:
        """Return the embedding dimensionality of the loaded model."""
        model = self._load_model()
        return model.get_sentence_embedding_dimension()

    @property
    def is_ready(self) -> bool:
        return self._model is not None


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
embedding_service = EmbeddingService()
