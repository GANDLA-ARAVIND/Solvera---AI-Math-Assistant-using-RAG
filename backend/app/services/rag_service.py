"""RAG service — retrieves relevant knowledge-base chunks via FAISS + SentenceTransformers."""

import logging
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)


class RAGService:
    """Thin wrapper around the FAISS vector store that provides the same
    public API the rest of the codebase already depends on."""

    def __init__(self):
        self._store = vector_store

    # ------------------------------------------------------------------
    # Startup helper (called from main.py lifespan)
    # ------------------------------------------------------------------
    def initialize(self) -> None:
        """Load (or build) the FAISS index so retrieval is ready."""
        if self._store.is_ready:
            return

        loaded = self._store.load()
        if loaded:
            logger.info("RAG service ready  (%d vectors)", self._store.total_vectors)
        else:
            logger.warning(
                "FAISS index not found. Run `python -m app.knowledge_base.seed_data` "
                "to build it."
            )

    # ------------------------------------------------------------------
    # Public API (unchanged signatures for backward-compat)
    # ------------------------------------------------------------------
    def is_ready(self) -> bool:
        return self._store.is_ready

    def retrieve(
        self, query: str, n_results: int = 5, topic_filter: str | None = None
    ) -> list[dict]:
        """Retrieve relevant math knowledge for the given query.

        Returns a list of dicts with keys: ``content``, ``metadata``, ``relevance_score``.
        """
        if not self.is_ready():
            return []

        results = self._store.search(
            query=query, top_k=n_results, topic_filter=topic_filter
        )

        # Fallback: if topic filter yielded nothing, retry without it
        if not results and topic_filter and topic_filter != "general_math":
            results = self._store.search(query=query, top_k=n_results)

        return results

    def retrieve_top3(
        self, query: str, topic_filter: str | None = None
    ) -> list[dict]:
        """Retrieve top 3 most relevant results — formula, concept, and example.

        This is the preferred retrieval method for the hybrid pipeline.
        Returns a list of dicts with keys: ``content``, ``metadata``, ``relevance_score``.
        """
        return self.retrieve(query, n_results=3, topic_filter=topic_filter)

    def format_context(self, retrieved_docs: list[dict]) -> str:
        """Format retrieved documents into a context string for the LLM."""
        if not retrieved_docs:
            return "No specific reference material found. Use your mathematical knowledge."

        context_parts = []
        for i, doc in enumerate(retrieved_docs, 1):
            meta = doc["metadata"]
            score = doc.get("relevance_score", 0)
            part = (
                f"[Reference {i} (score {score:.3f}): {meta.get('title', 'Unknown')} "
                f"({meta.get('topic', '')}/{meta.get('subtopic', '')})]\n"
                f"{doc['content']}\n"
            )
            formula = meta.get("formula_latex", "")
            if formula:
                part += f"LaTeX formula: {formula}\n"
            context_parts.append(part)

        return "\n---\n".join(context_parts)

    def format_context_structured(self, retrieved_docs: list[dict]) -> str:
        """Format top 3 results into structured sections: Formula, Concept, Example."""
        if not retrieved_docs:
            return "No specific reference material found."

        sections = []
        labels = ["FORMULA / DEFINITION", "RELATED CONCEPT", "SOLVED EXAMPLE"]

        for i, doc in enumerate(retrieved_docs[:3]):
            meta = doc["metadata"]
            label = labels[i] if i < len(labels) else f"Reference {i + 1}"
            score = doc.get("relevance_score", 0)

            part = (
                f"[{label} (score {score:.3f})]\n"
                f"Title: {meta.get('title', 'Unknown')}\n"
                f"Topic: {meta.get('topic', '')}/{meta.get('subtopic', '')}\n"
                f"{doc['content']}\n"
            )
            formula = meta.get("formula_latex", "")
            if formula:
                part += f"Formula: {formula}\n"
            sections.append(part)

        return "\n---\n".join(sections)


# Singleton instance
rag_service = RAGService()
