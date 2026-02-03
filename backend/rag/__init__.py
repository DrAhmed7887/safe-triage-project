"""SAFE-Triage RAG package."""

import os

DISABLE_RAG = os.getenv("DISABLE_RAG", "false").lower() == "true"

if not DISABLE_RAG:
    from .document_processor import process_all_documents
    from .vector_store import build_vector_store
    from .retriever import retrieve
    __all__ = ["process_all_documents", "build_vector_store", "retrieve"]
else:
    # Stub functions when RAG is disabled
    def process_all_documents(*args, **kwargs):
        return []
    def build_vector_store(*args, **kwargs):
        return None
    def retrieve(*args, **kwargs):
        return []
    __all__ = ["process_all_documents", "build_vector_store", "retrieve"]
    print("[RAG] Disabled via DISABLE_RAG environment variable")
