"""SAFE-Triage RAG package."""

from .document_processor import process_all_documents
from .vector_store import build_vector_store
from .retriever import retrieve

__all__ = ["process_all_documents", "build_vector_store", "retrieve"]
