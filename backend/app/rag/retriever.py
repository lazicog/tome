import chromadb
from rank_bm25 import BM25Okapi

from app.config import settings
from app.rag.embeddings import embed_query


client = chromadb.PersistentClient(path=str(settings.chroma_dir))


def _collection_name(book_id: str) -> str:
    return f"book_{book_id}"


def add_chunks(book_id: str, chunks: list[dict], embeddings: list[list[float]]) -> None:
    collection = client.get_or_create_collection(name=_collection_name(book_id), metadata={"hnsw:space": "cosine"})
    collection.add(
        ids=[c["id"] for c in chunks],
        documents=[c["content"] for c in chunks],
        metadatas=[c["metadata"] for c in chunks],
        embeddings=embeddings,
    )


def search_chunks(book_id: str, query: str, k: int = 5) -> list[dict]:
    collection = client.get_or_create_collection(name=_collection_name(book_id), metadata={"hnsw:space": "cosine"})
    query_vec = embed_query(query)

    vector = collection.query(query_embeddings=[query_vec], n_results=k * 3)
    docs = vector.get("documents", [[]])[0]
    metas = vector.get("metadatas", [[]])[0]
    ids = vector.get("ids", [[]])[0]
    distances = vector.get("distances", [[]])[0]

    if not docs:
        return []

    tokenized = [d.split() for d in docs]
    bm25 = BM25Okapi(tokenized)
    bm_scores = bm25.get_scores(query.split())

    merged: list[dict] = []
    for i, doc in enumerate(docs):
        distance = distances[i] if i < len(distances) else 1.0
        vec_score = max(0.0, 1.0 - float(distance))
        bm_score = float(bm_scores[i]) if i < len(bm_scores) else 0.0
        score = (0.7 * vec_score) + (0.3 * bm_score)
        merged.append(
            {
                "id": ids[i],
                "content": doc,
                "metadata": metas[i],
                "score": score,
            }
        )

    merged.sort(key=lambda x: x["score"], reverse=True)
    return merged[:k]
