import json
import structlog
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.agents.graph import stream_routed_answer
from app.agents.tutor import _sse_event, stream_tutor_answer
from app.config import settings
from app.schemas import ChatMessage, ChatRequest, ProcessingStatus
from app.services.storage_provider import get_book

router = APIRouter(prefix="/books", tags=["chat"])
log = structlog.get_logger()


def _parse_frame_data(frame: str, event: str) -> str | None:
    """Extract the data payload from an SSE frame for a given event name."""
    if not frame.startswith(f"event: {event}\n"):
        return None
    if "data: " not in frame:
        return None
    return frame.split("data: ", 1)[1].split("\n")[0]


async def _note_aware_stream(
    book_id: str,
    message: str,
    inner: AsyncIterator[str],
) -> AsyncIterator[str]:
    """Wraps any agent stream to auto-save summarize output as a note.

    Applied to all chat code paths so note auto-save works regardless of
    whether use_sqlite_storage is enabled.
    """
    collected_text = ""
    agent_type: str | None = None

    async for frame in inner:
        data = _parse_frame_data(frame, "token")
        if data is not None:
            try:
                collected_text += json.loads(data)
            except (json.JSONDecodeError, IndexError):
                pass
        else:
            data = _parse_frame_data(frame, "agent")
            if data is not None:
                try:
                    agent_type = json.loads(data)
                except (json.JSONDecodeError, IndexError):
                    pass
        yield frame

    if agent_type == "summarize" and collected_text:
        from app.services.notes import create_note
        try:
            title = f"Notes: {message[:80]}"
            await create_note(book_id=book_id, content=collected_text, title=title, note_type="ai_summary")
            yield _sse_event("note_saved", {"title": title})
        except Exception as exc:
            log.warning("note_autosave.failed", book_id=book_id, error=str(exc))


async def _session_aware_stream(
    book_id: str,
    message: str,
    history: list[ChatMessage],
    session_id: str,
    current_page: int | None = None,
) -> AsyncIterator[str]:
    """Wraps the agent stream to persist messages and emit session metadata."""
    from app.services.sessions import add_message

    await add_message(session_id, "user", message)

    yield _sse_event("session", session_id)

    if settings.phase2_routing_enabled:
        inner: AsyncIterator[str] = stream_routed_answer(book_id=book_id, message=message, history=history, current_page=current_page)
    else:
        inner = stream_tutor_answer(book_id=book_id, message=message, history=history, current_page=current_page)

    collected_text = ""
    agent_type: str | None = None

    async for frame in inner:
        data = _parse_frame_data(frame, "token")
        if data is not None:
            try:
                collected_text += json.loads(data)
            except (json.JSONDecodeError, IndexError):
                pass
        else:
            data = _parse_frame_data(frame, "agent")
            if data is not None:
                try:
                    agent_type = json.loads(data)
                except (json.JSONDecodeError, IndexError):
                    pass
        yield frame

    if collected_text:
        await add_message(session_id, "assistant", collected_text, agent_type=agent_type)


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

    current_page = payload.current_page

    if settings.use_sqlite_storage:
        from app.services.sessions import create_session

        session_id = payload.session_id
        if not session_id:
            session_id = await create_session(book_id)

        base_stream: AsyncIterator[str] = _session_aware_stream(
            book_id=book_id,
            message=payload.message,
            history=history,
            session_id=session_id,
            current_page=current_page,
        )
    elif settings.phase2_routing_enabled:
        base_stream = stream_routed_answer(book_id=book_id, message=payload.message, history=history, current_page=current_page)
    else:
        base_stream = stream_tutor_answer(book_id=book_id, message=payload.message, history=history, current_page=current_page)

    stream = _note_aware_stream(book_id=book_id, message=payload.message, inner=base_stream)
    return StreamingResponse(stream, media_type="text/event-stream")
