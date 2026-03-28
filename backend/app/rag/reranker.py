import structlog
from sentence_transformers import CrossEncoder

from app.config import settings

log = structlog.get_logger()

_RERANKER: CrossEncoder | None = None


def _load_reranker() -> CrossEncoder:
    global _RERANKER
    if _RERANKER is None:
        log.info("reranker.loading", model=settings.reranker_model)
        _RERANKER = CrossEncoder(settings.reranker_model)
        log.info("reranker.loaded", model=settings.reranker_model)
    return _RERANKER


def rerank_chunks(query: str, chunks: list[dict], top_k: int | None = None) -> list[dict]:
    """Re-score chunks using a cross-encoder and return sorted by relevance."""
    if not chunks or not settings.reranker_enabled:
        return chunks

    model = _load_reranker()
    pairs = [(query, c["content"]) for c in chunks]
    scores = model.predict(pairs)

    for i, chunk in enumerate(chunks):
        chunk["rerank_score"] = float(scores[i])

    reranked = sorted(chunks, key=lambda x: x["rerank_score"], reverse=True)

    if top_k:
        reranked = reranked[:top_k]

    log.info(
        "reranker.done",
        candidates=len(chunks),
        returned=len(reranked),
        top_score=round(reranked[0]["rerank_score"], 4) if reranked else 0,
    )
    return reranked
