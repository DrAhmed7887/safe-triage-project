"""
RAG Retriever for SAFE-Triage
Queries Chroma DB for top-k relevant chunks.
"""

from typing import List, Dict, Optional

from .vector_store import (
    get_collection,
    embed_texts,
    DEFAULT_COLLECTION,
    DEFAULT_PERSIST_DIR,
    DEFAULT_EMBEDDING_MODEL,
)


def retrieve(
    query: str,
    k: int = 5,
    persist_dir: str = DEFAULT_PERSIST_DIR,
    collection_name: str = DEFAULT_COLLECTION,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
) -> List[Dict]:
    """Retrieve top-k chunks for a query."""
    _, collection = get_collection(persist_dir, collection_name)
    query_embedding = embed_texts([query], model_name=model_name)[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k,
        include=["documents", "metadatas", "distances", "ids"],
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]
    ids = results.get("ids", [[]])[0]

    output = []
    for doc, meta, dist, doc_id in zip(documents, metadatas, distances, ids):
        output.append(
            {
                "id": doc_id,
                "text": doc,
                "metadata": meta,
                "distance": dist,
            }
        )
    return output


if __name__ == "__main__":
    q = "ESI level 2 high risk criteria"
    hits = retrieve(q, k=3)
    for i, h in enumerate(hits, start=1):
        print(f"\n#{i} ({h['metadata'].get('source')}) distance={h['distance']:.4f}")
        print(h["text"][:300] + "...")
