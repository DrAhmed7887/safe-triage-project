"""
RAG Retriever for SAFE-Triage
Cached wrapper over SimpleVectorStore retrieval.
"""

import os
from typing import List, Dict, Optional

__all__ = ["retrieve"]

# Disable RAG to save memory on constrained environments (Render free tier)
DISABLE_RAG = os.getenv("DISABLE_RAG", "false").lower() == "true"

_STORE = None


def _get_store():
    global _STORE
    if DISABLE_RAG:
        return None
    if _STORE is None:
        from .vector_store import SimpleVectorStore
        _STORE = SimpleVectorStore()
    return _STORE


def retrieve(query: str, k: int = 5, source_filter: Optional[str] = None) -> List[Dict]:
    """Retrieve relevant chunks for a query."""
    if DISABLE_RAG:
        return []
    store = _get_store()
    if store is None:
        return []
    return store.search(query, k=k, source_filter=source_filter)


if __name__ == "__main__":
    q = "ESI level 2 high risk criteria"
    hits = retrieve(q, k=3)
    for i, h in enumerate(hits, start=1):
        print(f"\n#{i} ({h['source']}) score={h['score']:.4f}")
        print(h["text"][:300] + "...")
