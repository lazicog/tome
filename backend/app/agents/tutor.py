import json
from typing import AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.config import settings
from app.rag.retriever import search_chunks
from app.schemas import ChatMessage
from app.services.llm import get_chat_model_with_fallback

TUTOR_PROMPT = """You are Tome Tutor, a concise technical teacher.
Use only the context below to answer.
If context is missing, say what is missing and ask for a clearer question.

Context:
{context}
"""


def _sse_event(event: str, payload: str | list[dict]) -> str:
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


def _format_sources(chunks: list[dict]) -> list[dict]:
    seen_pages: set[tuple[str, str]] = set()
    sources: list[dict] = []
    for c in chunks:
        chapter = c["metadata"].get("chapter", "Unknown")
        pages_key = (chapter, ",".join(str(p) for p in c["metadata"].get("page_numbers", [])))
        if pages_key in seen_pages:
            continue
        seen_pages.add(pages_key)

        score = c.get("rerank_score", c.get("score", 0.0))
        sources.append({
            "chunk_id": c["id"],
            "chapter": chapter,
            "section": c["metadata"].get("section", "Unknown"),
            "page_numbers": c["metadata"].get("page_numbers", []),
            "score": round(float(score), 4),
            "relevance": _relevance_label(float(score)),
            "quote": _extract_quote(c.get("content", "")),
        })
    return sources


def build_context(chunks: list[dict]) -> str:
    return "\n\n".join([chunk["content"] for chunk in chunks])


async def stream_tutor_answer(book_id: str, message: str, history: list[ChatMessage]) -> AsyncIterator[str]:
    chunks = search_chunks(book_id=book_id, query=message, k=settings.top_k_chunks)
    context = build_context(chunks)
    sources = _format_sources(chunks)

    llm = get_chat_model_with_fallback()
    prompt_messages = [
        SystemMessage(content=TUTOR_PROMPT.format(context=context)),
        *_history_to_messages(history),
        HumanMessage(content=message),
    ]

    yield _sse_event("agent", "explain")

    async for chunk in llm.astream(prompt_messages):
        token = chunk.content
        if token:
            yield _sse_event("token", token)

    yield _sse_event("sources", sources)
    yield _sse_event("done", "")


async def stream_prompted_answer(
    *,
    system_prompt: str,
    context: str,
    message: str,
    history: list[ChatMessage],
    sources: list[dict],
    agent_type: str | None = None,
) -> AsyncIterator[str]:
    llm = get_chat_model_with_fallback()
    prompt_messages = [
        SystemMessage(content=system_prompt.format(context=context)),
        *_history_to_messages(history),
        HumanMessage(content=message),
    ]

    if agent_type:
        yield _sse_event("agent", agent_type)

    async for chunk in llm.astream(prompt_messages):
        token = chunk.content
        if token:
            yield _sse_event("token", token)

    yield _sse_event("sources", sources)
    yield _sse_event("done", "")
