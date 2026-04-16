"""FAISS-backed vector store for fast similarity search over knowledge-base chunks."""

import json
import logging
import os
from pathlib import Path

import faiss
import numpy as np

from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)


class FAISSVectorStore:
    """Wraps a FAISS index together with the metadata for each stored vector."""

    def __init__(self, index_dir: str = "./faiss_index"):
        self.index_dir = Path(index_dir)
        self.index: faiss.Index | None = None
        self.documents: list[dict] = []  # parallel list – one dict per vector
        self._ready = False

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    @property
    def _index_path(self) -> Path:
        return self.index_dir / "index.faiss"

    @property
    def _meta_path(self) -> Path:
        return self.index_dir / "metadata.json"

    def save(self) -> None:
        """Persist index + metadata to disk."""
        self.index_dir.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self._index_path))
        with open(self._meta_path, "w", encoding="utf-8") as f:
            json.dump(self.documents, f, ensure_ascii=False)
        logger.info(
            "FAISS index saved (%d vectors) → %s", self.index.ntotal, self.index_dir
        )

    def load(self) -> bool:
        """Load a previously saved index from disk. Returns True on success."""
        if not self._index_path.exists() or not self._meta_path.exists():
            logger.warning("No FAISS index found at %s", self.index_dir)
            return False

        self.index = faiss.read_index(str(self._index_path))
        with open(self._meta_path, "r", encoding="utf-8") as f:
            self.documents = json.load(f)

        if self.index.ntotal != len(self.documents):
            logger.error(
                "Index / metadata length mismatch (%d vs %d). Rebuild required.",
                self.index.ntotal,
                len(self.documents),
            )
            self.index = None
            self.documents = []
            return False

        self._ready = True
        logger.info(
            "FAISS index loaded: %d vectors, dim=%d",
            self.index.ntotal,
            self.index.d,
        )
        return True

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------
    def build_index(
        self,
        texts: list[str],
        metadatas: list[dict],
        use_ivf: bool = False,
        nlist: int = 10,
    ) -> None:
        """Create a new FAISS index from raw texts.

        Args:
            texts: Document strings to embed and index.
            metadatas: Parallel list of metadata dicts (one per document).
            use_ivf: If True, build an IVF index for faster search on large datasets.
                     Falls back to flat index for small collections.
            nlist: Number of Voronoi cells (only used when ``use_ivf=True``).
        """
        if len(texts) != len(metadatas):
            raise ValueError("texts and metadatas must have the same length")

        logger.info("Encoding %d documents …", len(texts))
        embeddings = embedding_service.encode(texts, show_progress=True)
        dim = embeddings.shape[1]

        # Choose index type
        n_vectors = len(texts)
        if use_ivf and n_vectors >= 4 * nlist:
            quantizer = faiss.IndexFlatIP(dim)
            self.index = faiss.IndexIVFFlat(quantizer, dim, nlist, faiss.METRIC_INNER_PRODUCT)
            self.index.train(embeddings)
            logger.info("Built IVF index (nlist=%d)", nlist)
        else:
            # Flat index — exact search, fastest for < ~50 k vectors
            self.index = faiss.IndexFlatIP(dim)
            logger.info("Built Flat IP index (dim=%d)", dim)

        self.index.add(embeddings)

        # Store metadata alongside a copy of the document text
        self.documents = []
        for i, meta in enumerate(metadatas):
            entry = {**meta, "text": texts[i]}
            self.documents.append(entry)

        self._ready = True
        logger.info("Indexed %d vectors", self.index.ntotal)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    def search(
        self,
        query: str,
        top_k: int = 5,
        topic_filter: str | None = None,
        score_threshold: float = 0.0,
    ) -> list[dict]:
        """Retrieve the top-k most similar documents for a query.

        Args:
            query: Natural-language query string.
            top_k: Number of results to return.
            topic_filter: If set, only return docs whose ``topic`` metadata matches.
            score_threshold: Minimum similarity score to include a result.

        Returns:
            List of dicts with keys ``content``, ``metadata``, ``relevance_score``.
        """
        if not self.is_ready:
            logger.warning("FAISS index not ready — returning empty results")
            return []

        query_vec = embedding_service.encode_query(query)

        # If topic filtering is requested we over-fetch, then filter in Python.
        fetch_k = top_k * 4 if topic_filter else top_k
        fetch_k = min(fetch_k, self.index.ntotal)  # can't fetch more than we have

        scores, indices = self.index.search(query_vec, fetch_k)
        scores = scores[0]
        indices = indices[0]

        results: list[dict] = []
        for score, idx in zip(scores, indices):
            if idx == -1:
                continue
            if score < score_threshold:
                continue

            doc = self.documents[idx]

            # Apply topic filter
            if topic_filter and topic_filter != "general_math":
                if doc.get("topic", "") != topic_filter:
                    continue

            results.append(
                {
                    "content": doc["text"],
                    "metadata": {
                        k: v for k, v in doc.items() if k != "text"
                    },
                    "relevance_score": float(score),
                }
            )

            if len(results) >= top_k:
                break

        return results

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    @property
    def is_ready(self) -> bool:
        return self._ready and self.index is not None and self.index.ntotal > 0

    @property
    def total_vectors(self) -> int:
        return self.index.ntotal if self.index else 0

    def __repr__(self) -> str:
        status = "ready" if self.is_ready else "not ready"
        n = self.total_vectors
        return f"<FAISSVectorStore status={status} vectors={n}>"


# ---------------------------------------------------------------------------
# Module-level singleton  (index_dir is set from config at init time)
# ---------------------------------------------------------------------------
from app.config import FAISS_INDEX_DIR  # noqa: E402

vector_store = FAISSVectorStore(index_dir=FAISS_INDEX_DIR)
