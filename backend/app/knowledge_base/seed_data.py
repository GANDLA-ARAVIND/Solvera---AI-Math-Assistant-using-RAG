"""Build the FAISS vector index from the JSON knowledge-base files.

Run standalone:
    python -m app.knowledge_base.seed_data          (from backend/)

Or import and call ``seed_knowledge_base()`` programmatically.
"""

import json
import logging
import os
import sys

# Ensure the backend package is importable when run as a script
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.config import FAISS_INDEX_DIR  # noqa: E402
from app.services.vector_store import FAISSVectorStore  # noqa: E402

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def _load_json_entries() -> tuple[list[str], list[dict]]:
    """Read every JSON file in ``data/`` and return parallel lists of
    (document_texts, metadata_dicts)."""
    all_texts: list[str] = []
    all_metas: list[dict] = []

    for filename in sorted(os.listdir(DATA_DIR)):
        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(DATA_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            try:
                entries = json.load(f)
            except json.JSONDecodeError as exc:
                print(f"  ERROR parsing {filename}: {exc}")
                continue

        count = 0
        for entry in entries:
            # Build the text chunk that will be embedded
            doc_text = f"{entry['title']}. {entry['content']}"
            if entry.get("example"):
                doc_text += f" Example: {entry['example']}"

            metadata = {
                "id": entry.get("id", ""),
                "topic": entry.get("topic", ""),
                "subtopic": entry.get("subtopic", ""),
                "title": entry.get("title", ""),
                "formula_latex": entry.get("formula_latex", ""),
                "difficulty": entry.get("difficulty", "intermediate"),
                "source_file": filename,
            }

            all_texts.append(doc_text)
            all_metas.append(metadata)
            count += 1

        print(f"  Loaded {count} entries from {filename}")

    return all_texts, all_metas


def seed_knowledge_base(index_dir: str | None = None) -> FAISSVectorStore:
    """Embed all knowledge-base documents and persist a FAISS index.

    Args:
        index_dir: Override for the index directory (defaults to config).

    Returns:
        The populated ``FAISSVectorStore`` instance.
    """
    target_dir = index_dir or FAISS_INDEX_DIR

    texts, metas = _load_json_entries()
    if not texts:
        print("No documents found to seed!")
        return None

    store = FAISSVectorStore(index_dir=target_dir)
    store.build_index(texts, metas)
    store.save()

    print(f"\nSeeded {store.total_vectors} vectors into FAISS index → {target_dir}")
    return store


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Seeding Solvera knowledge base (FAISS) …\n")
    seed_knowledge_base()
    print("\nDone!")
