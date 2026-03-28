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


def _format_sources(chunks: list[dict]) -> list[dict]:
    return [
        {
            "chunk_id": c["id"],
            "chapter": c["metadata"].get("chapter", "Unknown"),
            "section": c["metadata"].get("section", "Unknown"),
            "page_numbers": c["metadata"].get("page_numbers", []),
            "score": round(float(c["score"]), 4),
        }
        for c in chunks
    ]


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
) -> AsyncIterator[str]:
    llm = get_chat_model_with_fallback()
    prompt_messages = [
        SystemMessage(content=system_prompt.format(context=context)),
        *_history_to_messages(history),
        HumanMessage(content=message),
    ]

    async for chunk in llm.astream(prompt_messages):
        token = chunk.content
        if token:
            yield _sse_event("token", token)

    yield _sse_event("sources", sources)
    yield _sse_event("done", "")
