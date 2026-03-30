from fastapi import APIRouter, HTTPException, Query

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


@router.get("/evals", summary="List recent LLM-as-judge eval results for a book")
async def debug_list_evals(
    book_id: str = Query(..., description="Book ID"),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    from app.services.evals import eval_stats, list_evals

    evals = await list_evals(book_id, limit=limit)
    stats = await eval_stats(book_id)
    return {"book_id": book_id, "stats": stats, "evals": evals}


@router.get("/evals/{eval_id}", summary="Get a single eval record")
async def debug_get_eval(eval_id: str) -> dict:
    from app.services.evals import get_eval

    record = await get_eval(eval_id)
    if not record:
        raise HTTPException(status_code=404, detail="Eval not found")
    return record
