"""
Vector Store for SAFE-Triage RAG
Builds and queries Chroma DB with sentence-transformer embeddings.
"""

import os
from typing import List, Dict, Optional, Tuple, Any, TYPE_CHECKING

from sentence_transformers import SentenceTransformer

from .document_processor import process_all_documents

if TYPE_CHECKING:
    import chromadb
    from chromadb.config import Settings

DEFAULT_COLLECTION = "safe_triage_guidelines"
DEFAULT_PERSIST_DIR = os.path.join(os.path.dirname(__file__), "chroma")
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

_EMBEDDER = None
_EMBEDDER_NAME = None


def get_embedder(model_name: str = DEFAULT_EMBEDDING_MODEL) -> SentenceTransformer:
    """Lazy-load and return embedding model."""
    global _EMBEDDER, _EMBEDDER_NAME
    if _EMBEDDER is None or _EMBEDDER_NAME != model_name:
        _EMBEDDER = SentenceTransformer(model_name)
        _EMBEDDER_NAME = model_name
    return _EMBEDDER


def embed_texts(texts: List[str], model_name: str = DEFAULT_EMBEDDING_MODEL) -> List[List[float]]:
    """Generate embeddings for a list of texts."""
    model = get_embedder(model_name)
    vectors = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    return vectors.tolist()


def _load_chromadb():
    """Load ChromaDB with a compatibility shim for pydantic v2."""
    try:
        import pydantic
        if not hasattr(pydantic, "BaseSettings"):
            try:
                from pydantic_settings import BaseSettings as _BaseSettings
                pydantic.BaseSettings = _BaseSettings
            except Exception as exc:  # pragma: no cover - env specific
                raise ImportError(
                    "pydantic-settings is required for chromadb with pydantic v2"
                ) from exc
        import chromadb
        from chromadb.config import Settings
        return chromadb, Settings
    except Exception:
        raise


def get_collection(
    persist_dir: str = DEFAULT_PERSIST_DIR,
    collection_name: str = DEFAULT_COLLECTION,
) -> Tuple[Any, Any]:
    """Get or create a Chroma collection."""
    chromadb, Settings = _load_chromadb()
    client = chromadb.PersistentClient(
        path=persist_dir,
        settings=Settings(anonymized_telemetry=False),
    )
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    return client, collection


def add_chunks_to_collection(
    collection: Any,
    chunks: List[Dict],
    batch_size: int = 64,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
) -> int:
    """Add chunked documents to a collection in batches."""
    total_added = 0
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]
        documents = [c["text"] for c in batch]
        ids = [c["chunk_id"] for c in batch]
        metadatas = [{"source": c["source"]} for c in batch]
        embeddings = embed_texts(documents, model_name=model_name)
        collection.add(
            documents=documents,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas,
        )
        total_added += len(batch)
    return total_added


def build_vector_store(
    documents_dir: str,
    persist_dir: str = DEFAULT_PERSIST_DIR,
    collection_name: str = DEFAULT_COLLECTION,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    force_rebuild: bool = False,
) -> Tuple[Any, Any]:
    """
    Build or load the vector store from documents.

    If force_rebuild is False and collection has data, it returns existing store.
    """
    client, collection = get_collection(persist_dir, collection_name)

    if not force_rebuild and collection.count() > 0:
        return client, collection

    if force_rebuild and collection.count() > 0:
        client.delete_collection(collection_name)
        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    chunks = process_all_documents(documents_dir)
    add_chunks_to_collection(collection, chunks, model_name=model_name)
    return client, collection


if __name__ == "__main__":
    docs_dir = os.path.join(os.path.dirname(__file__), "documents")
    _, collection = build_vector_store(docs_dir, force_rebuild=False)
    print(f"Vector store ready: {collection.count()} chunks")
