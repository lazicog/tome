"""Thin wrapper kept for API compatibility — delegates to the orchestrator."""

from typing import AsyncIterator

from app.agents.orchestrator import EvalMetadata, stream_orchestrated_answer
from app.schemas import ChatMessage


async def stream_routed_answer(
    book_id: str,
    message: str,
    history: list[ChatMessage],
    current_page: int | None = None,
) -> AsyncIterator[str | EvalMetadata]:
    async for event in stream_orchestrated_answer(book_id, message, history, current_page):
        yield event
