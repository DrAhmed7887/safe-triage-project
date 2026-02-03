"""
RAG Retriever for SAFE-Triage
Thin wrapper over SimpleVectorStore retrieval.
"""

from typing import List, Dict, Optional

from .vector_store import retrieve

__all__ = ["retrieve"]

if __name__ == "__main__":
    q = "ESI level 2 high risk criteria"
    hits = retrieve(q, k=3)
    for i, h in enumerate(hits, start=1):
        print(f"\n#{i} ({h['source']}) score={h['score']:.4f}")
        print(h["text"][:300] + "...")
