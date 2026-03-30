"""SSE and RAG utility helpers shared across agent modules."""

import json

from langchain_core.messages import AIMessage, HumanMessage

from app.schemas import ChatMessage


def _sse_event(event: str, payload: str | list[dict] | dict) -> str:
    encoded = json.dumps(payload)
    lines = encoded.splitlines() or [encoded]
    data_lines = "".join(f"data: {line}\n" for line in lines)
    return f"event: {event}\n{data_lines}\n"


def _history_to_messages(history: list[ChatMessage]) -> list[HumanMessage | AIMessage]:
    output: list[HumanMessage | AIMessage] = []
    for msg in history:
        if msg.role == "assistant":
            output.append(AIMessage(content=msg.content))
        else:
            output.append(HumanMessage(content=msg.content))
    return output


def _extract_quote(content: str, max_len: int = 160) -> str:
    """Pull the first meaningful sentence(s) from a chunk as a preview quote."""
    text = content
    if text.startswith("["):
        newline_pos = text.find("\n\n")
        if newline_pos != -1:
            text = text[newline_pos + 2:]
    sentences = text.replace("\n", " ").split(". ")
    quote = ". ".join(sentences[:2]).strip()
    if len(quote) > max_len:
        quote = quote[:max_len].rsplit(" ", 1)[0] + "..."
    return quote


def _relevance_label(score: float) -> str:
    if score >= 0.7:
        return "high"
    if score >= 0.4:
        return "medium"
    return "low"


def _format_sources(chunks: list[dict], current_page: int | None = None) -> list[dict]:
    seen_pages: set[tuple[str, str]] = set()
    sources: list[dict] = []
    for c in chunks:
        chapter = c["metadata"].get("chapter", "Unknown")
        pages_key = (chapter, ",".join(str(p) for p in c["metadata"].get("page_numbers", [])))
        if pages_key in seen_pages:
            continue
        seen_pages.add(pages_key)

        score = c.get("rerank_score", c.get("score", 0.0))
        page_numbers: list[int] = c["metadata"].get("page_numbers", [])
        is_ahead = (
            current_page is not None
            and bool(page_numbers)
            and any(p > current_page for p in page_numbers)
        )
        sources.append({
            "chunk_id": c["id"],
            "chapter": chapter,
            "section": c["metadata"].get("section", "Unknown"),
            "page_numbers": page_numbers,
            "score": round(float(score), 4),
            "relevance": _relevance_label(float(score)),
            "quote": _extract_quote(c.get("content", "")),
            "is_ahead_of_position": is_ahead,
        })
    return sources


def build_context(chunks: list[dict]) -> str:
    return "\n\n".join([chunk["content"] for chunk in chunks])
