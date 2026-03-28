from fastapi import APIRouter, Query

from app.rag.retriever import search_chunks

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/retrieve", summary="Inspect raw retrieval results for a query")
async def debug_retrieve(
    book_id: str = Query(..., description="Book ID to search"),
    query: str = Query(..., description="Search query"),
    k: int = Query(default=8, description="Number of chunks to return"),
) -> dict:
    chunks = search_chunks(book_id=book_id, query=query, k=k)
    return {
        "book_id": book_id,
        "query": query,
        "k": k,
        "results": [
            {
                "id": c["id"],
                "score": round(c["score"], 4),
                "chapter": c["metadata"].get("chapter", "Unknown"),
                "section": c["metadata"].get("section", "Unknown"),
                "page_numbers": c["metadata"].get("page_numbers", []),
                "content_preview": c["content"][:300],
            }
            for c in chunks
        ],
    }
