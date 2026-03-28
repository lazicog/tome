import json
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.agents.graph import stream_routed_answer
from app.agents.tutor import _sse_event, stream_tutor_answer
from app.config import settings
from app.schemas import ChatMessage, ChatRequest, ProcessingStatus
from app.services.storage_provider import get_book

router = APIRouter(prefix="/books", tags=["chat"])


async def _session_aware_stream(
    book_id: str,
    message: str,
    history: list[ChatMessage],
    session_id: str,
) -> AsyncIterator[str]:
    """Wraps the agent stream to persist messages, run tools, and emit session metadata."""
    from app.services.sessions import add_message

    await add_message(session_id, "user", message)

    yield _sse_event("session", session_id)

    inner: AsyncIterator[str]
    if settings.phase2_routing_enabled:
        inner = stream_routed_answer(book_id=book_id, message=message, history=history)
    else:
        inner = stream_tutor_answer(book_id=book_id, message=message, history=history)

    collected_text = ""
    agent_type: str | None = None

    async for frame in inner:
        if frame.startswith("event: token\n"):
            data_part = frame.split("data: ", 1)[1].split("\n")[0] if "data: " in frame else ""
            try:
                collected_text += json.loads(data_part)
            except (json.JSONDecodeError, IndexError):
                pass
        elif frame.startswith("event: agent\n"):
            data_part = frame.split("data: ", 1)[1].split("\n")[0] if "data: " in frame else ""
            try:
                agent_type = json.loads(data_part)
            except (json.JSONDecodeError, IndexError):
                pass
        yield frame

    if collected_text:
        await add_message(session_id, "assistant", collected_text, agent_type=agent_type)

    if agent_type == "summarize" and collected_text:
        from app.services.notes import create_note
        try:
            title = f"Notes: {message[:80]}"
            await create_note(
                book_id=book_id,
                content=collected_text,
                title=title,
                note_type="ai_summary",
            )
            yield _sse_event("note_saved", {"title": title})
        except Exception:
            pass


@router.post("/{book_id}/chat", summary="Chat with a processed book")
async def chat_with_book(book_id: str, payload: ChatRequest) -> StreamingResponse:
    book = await get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if book.status != ProcessingStatus.ready:
        raise HTTPException(status_code=400, detail="Book is still processing")

    if settings.use_sqlite_storage and payload.session_id:
        from app.services.sessions import get_messages

        db_messages = await get_messages(payload.session_id)
        history = [ChatMessage(role=m["role"], content=m["content"]) for m in db_messages]
    else:
        history = payload.chat_history

    if settings.use_sqlite_storage:
        from app.services.sessions import create_session

        session_id = payload.session_id
        if not session_id:
            session_id = await create_session(book_id)

        stream = _session_aware_stream(
            book_id=book_id,
            message=payload.message,
            history=history,
            session_id=session_id,
        )
    elif settings.phase2_routing_enabled:
        stream = stream_routed_answer(book_id=book_id, message=payload.message, history=history)
    else:
        stream = stream_tutor_answer(book_id=book_id, message=payload.message, history=history)

    return StreamingResponse(stream, media_type="text/event-stream")
