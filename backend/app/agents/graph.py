"""Thin wrapper kept for API compatibility — delegates to the orchestrator."""

from app.agents.orchestrator import stream_orchestrated_answer
from app.schemas import ChatMessage


async def stream_routed_answer(
    book_id: str,
    message: str,
    history: list[ChatMessage],
    current_page: int | None = None,
):
    async for event in stream_orchestrated_answer(book_id, message, history, current_page):
        yield event
