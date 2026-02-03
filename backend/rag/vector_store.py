"""
Simple Vector Store using numpy + sentence-transformers
No ChromaDB dependency - works with Python 3.14
"""

import os
import json
from typing import List, Dict, Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from .document_processor import process_all_documents

# Multilingual model (Arabic + English)
DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_PERSIST_DIR = os.path.join(os.path.dirname(__file__), "vector_data")


class SimpleVectorStore:
    def __init__(self, persist_dir: str = DEFAULT_PERSIST_DIR, model_name: str = DEFAULT_MODEL):
        self.persist_dir = persist_dir
        os.makedirs(persist_dir, exist_ok=True)

        self.embeddings_file = os.path.join(persist_dir, "embeddings.npy")
        self.documents_file = os.path.join(persist_dir, "documents.json")

        print(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        print("Model loaded")

        self.embeddings = None
        self.documents = []
        self._load()

    def _load(self):
        """Load existing embeddings if available."""
        if os.path.exists(self.embeddings_file) and os.path.exists(self.documents_file):
            self.embeddings = np.load(self.embeddings_file)
            with open(self.documents_file, "r", encoding="utf-8") as f:
                self.documents = json.load(f)
            print(f"Loaded {len(self.documents)} existing chunks")

    def _save(self):
        """Persist embeddings to disk."""
        np.save(self.embeddings_file, self.embeddings)
        with open(self.documents_file, "w", encoding="utf-8") as f:
            json.dump(self.documents, f, ensure_ascii=False, indent=2)
        print(f"Saved {len(self.documents)} chunks to {self.persist_dir}")

    def add_documents(self, documents: List[Dict]):
        """Add documents with text, source, chunk_id."""
        if not documents:
            return

        texts = [doc["text"] for doc in documents]

        print(f"Generating embeddings for {len(texts)} chunks...")
        new_embeddings = self.model.encode(texts, show_progress_bar=True)

        if self.embeddings is None:
            self.embeddings = new_embeddings
        else:
            self.embeddings = np.vstack([self.embeddings, new_embeddings])

        self.documents.extend(documents)
        self._save()

    def search(self, query: str, k: int = 5, source_filter: Optional[str] = None) -> List[Dict]:
        """Search for similar documents."""
        if self.embeddings is None or len(self.documents) == 0:
            return []

        query_embedding = self.model.encode([query])[0]

        # Cosine similarity
        similarities = np.dot(self.embeddings, query_embedding) / (
            np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_embedding)
        )

        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1]

        results = []
        for idx in top_indices:
            doc = self.documents[idx]
            if source_filter and doc.get("source") != source_filter:
                continue
            results.append({
                "text": doc["text"],
                "source": doc.get("source", "unknown"),
                "chunk_id": doc.get("chunk_id", str(idx)),
                "score": float(similarities[idx]),
            })
            if len(results) >= k:
                break

        return results

    def count(self) -> int:
        return len(self.documents)


def build_vector_store(documents_dir: str = None, force_rebuild: bool = False) -> SimpleVectorStore:
    """Build or load the vector store."""
    if documents_dir is None:
        documents_dir = os.path.join(os.path.dirname(__file__), "documents")

    store = SimpleVectorStore()

    if store.count() > 0 and not force_rebuild:
        print(f"Vector store already has {store.count()} chunks. Skipping rebuild.")
        return store

    # Clear existing
    store.embeddings = None
    store.documents = []

    # Process and add documents
    chunks = process_all_documents(documents_dir)
    store.add_documents(chunks)

    return store


def retrieve(query: str, k: int = 5, source_filter: Optional[str] = None) -> List[Dict]:
    """Retrieve relevant chunks for a query."""
    store = SimpleVectorStore()
    return store.search(query, k=k, source_filter=source_filter)


if __name__ == "__main__":
    docs_dir = os.path.join(os.path.dirname(__file__), "documents")

    print("=" * 50)
    print("BUILDING VECTOR STORE")
    print("=" * 50)

    store = build_vector_store(docs_dir, force_rebuild=True)

    print("\n" + "=" * 50)
    print("TEST SEARCHES")
    print("=" * 50)

    tests = [
        ("chest pain diabetic", None),
        ("ESI level 1 immediate", "ESI_v5"),
        ("NEWS2 score 7", "NEWS2"),
        ("توثيق الطوارئ", "GAHAR"),
    ]

    for query, source in tests:
        suffix = f" [filter: {source}]" if source else ""
        print(f"\nQuery: '{query}'{suffix}")
        results = store.search(query, k=2, source_filter=source)
        for result in results:
            print(f"  [{result['source']}] score={result['score']:.3f}")
            print(f"  {result['text'][:120]}...")
