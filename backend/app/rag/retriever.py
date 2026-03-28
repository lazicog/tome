import structlog
import chromadb
from rank_bm25 import BM25Okapi

from app.config import settings
from app.rag.embeddings import embed_query

log = structlog.get_logger()

client = chromadb.PersistentClient(path=str(settings.chroma_dir))


def _collection_name(book_id: str) -> str:
    return f"book_{book_id}"


def _to_chroma_metadata(metadata: dict) -> dict:
    page_numbers = metadata.get("page_numbers", [])
    if isinstance(page_numbers, list):
        page_numbers_value = ",".join(str(x) for x in page_numbers)
    else:
        page_numbers_value = str(page_numbers)

    return {
        "book_id": metadata.get("book_id", ""),
        "chapter": metadata.get("chapter", "Unknown"),
        "section": metadata.get("section", "Unknown"),
        "page_numbers": page_numbers_value,
        "chunk_index": int(metadata.get("chunk_index", 0)),
        "content_type": metadata.get("content_type", "text"),
    }


def _from_chroma_metadata(metadata: dict) -> dict:
    raw_pages = metadata.get("page_numbers", "")
    if isinstance(raw_pages, str) and raw_pages.strip():
        page_numbers = [int(x) for x in raw_pages.split(",") if x.strip().isdigit()]
    else:
        page_numbers = []

    return {
        "book_id": metadata.get("book_id", ""),
        "chapter": metadata.get("chapter", "Unknown"),
        "section": metadata.get("section", "Unknown"),
        "page_numbers": page_numbers,
        "chunk_index": int(metadata.get("chunk_index", 0)),
        "content_type": metadata.get("content_type", "text"),
    }


def add_chunks(book_id: str, chunks: list[dict], embeddings: list[list[float]]) -> None:
    collection = client.get_or_create_collection(name=_collection_name(book_id), metadata={"hnsw:space": "cosine"})
    collection.add(
        ids=[c["id"] for c in chunks],
        documents=[c["content"] for c in chunks],
        metadatas=[_to_chroma_metadata(c["metadata"]) for c in chunks],
        embeddings=embeddings,
    )


def delete_collection(book_id: str) -> None:
    name = _collection_name(book_id)
    try:
        client.delete_collection(name=name)
        log.info("retriever.collection_deleted", book_id=book_id)
    except Exception:
        log.warning("retriever.collection_not_found", book_id=book_id)


def search_chunks(book_id: str, query: str, k: int = 5) -> list[dict]:
    collection = client.get_or_create_collection(name=_collection_name(book_id), metadata={"hnsw:space": "cosine"})
    query_vec = embed_query(query)

    prefetch = k * settings.retrieval_prefetch_multiplier
    vector = collection.query(query_embeddings=[query_vec], n_results=prefetch)
    docs = vector.get("documents", [[]])[0]
    metas = vector.get("metadatas", [[]])[0]
    ids = vector.get("ids", [[]])[0]
    distances = vector.get("distances", [[]])[0]

    if not docs:
        log.warning("retriever.no_results", book_id=book_id, query=query[:80])
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
                "metadata": _from_chroma_metadata(metas[i]),
                "score": score,
            }
        )

    merged.sort(key=lambda x: x["score"], reverse=True)

    threshold = settings.retrieval_score_threshold
    results = [c for c in merged[:k] if c["score"] >= threshold]

    log.info(
        "retriever.search",
        book_id=book_id,
        query=query[:80],
        prefetched=len(docs),
        returned=len(results),
        top_score=round(results[0]["score"], 4) if results else 0,
        low_score=round(results[-1]["score"], 4) if results else 0,
    )

    return results
