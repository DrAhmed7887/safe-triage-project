"""
RAG Retriever for SAFE-Triage
Cached wrapper over SimpleVectorStore retrieval.
"""

from typing import List, Dict, Optional

from .vector_store import SimpleVectorStore

__all__ = ["retrieve"]

_STORE: Optional[SimpleVectorStore] = None


def _get_store() -> SimpleVectorStore:
    global _STORE
    if _STORE is None:
        _STORE = SimpleVectorStore()
    return _STORE


def retrieve(query: str, k: int = 5, source_filter: Optional[str] = None) -> List[Dict]:
    """Retrieve relevant chunks for a query."""
    store = _get_store()
    return store.search(query, k=k, source_filter=source_filter)


if __name__ == "__main__":
    q = "ESI level 2 high risk criteria"
    hits = retrieve(q, k=3)
    for i, h in enumerate(hits, start=1):
        print(f"\n#{i} ({h['source']}) score={h['score']:.4f}")
        print(h["text"][:300] + "...")
