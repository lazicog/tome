import asyncio
import json
import structlog
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.agents.graph import stream_routed_answer
from app.agents.orchestrator import EvalMetadata
from app.agents.tutor import _sse_event
from app.config import settings
from app.schemas import ChatMessage, ChatRequest, ProcessingStatus
from app.services.storage_provider import get_book

router = APIRouter(prefix="/books", tags=["chat"])
log = structlog.get_logger()


def _parse_frame_data(frame: str, event: str) -> str | None:
    if not frame.startswith(f"event: {event}\n"):
        return None
    if "data: " not in frame:
        return None
    return frame.split("data: ", 1)[1].split("\n")[0]


async def _session_aware_stream(
    book_id: str,
    message: str,
    history: list[ChatMessage],
    session_id: str,
    current_page: int | None = None,
) -> AsyncIterator[str]:
    from app.services.sessions import add_message

    await add_message(session_id, "user", message)
    yield _sse_event("session", session_id)

    collected_text = ""
    eval_meta: EvalMetadata | None = None

    async for frame in stream_routed_answer(
        book_id=book_id,
        message=message,
        history=history,
        current_page=current_page,
    ):
        if isinstance(frame, EvalMetadata):
            eval_meta = frame
            continue

        data = _parse_frame_data(frame, "token")
        if data is not None:
            try:
                collected_text += json.loads(data)
            except (json.JSONDecodeError, IndexError):
                pass
        yield frame

    if collected_text:
        await add_message(session_id, "assistant", collected_text)

    if eval_meta is not None and collected_text:
        _fire_eval(book_id, message, collected_text, eval_meta, session_id)


async def _plain_stream(
    book_id: str,
    message: str,
    history: list[ChatMessage],
    current_page: int | None = None,
) -> AsyncIterator[str]:
    collected_text = ""
    eval_meta: EvalMetadata | None = None

    async for frame in stream_routed_answer(
        book_id=book_id,
        message=message,
        history=history,
        current_page=current_page,
    ):
        if isinstance(frame, EvalMetadata):
            eval_meta = frame
            continue

        data = _parse_frame_data(frame, "token")
        if data is not None:
            try:
                collected_text += json.loads(data)
            except (json.JSONDecodeError, IndexError):
                pass
        yield frame

    if eval_meta is not None and collected_text:
        _fire_eval(book_id, message, collected_text, eval_meta, None)


def _fire_eval(
    book_id: str,
    user_message: str,
    assistant_response: str,
    meta: EvalMetadata,
    session_id: str | None,
) -> None:
    """Schedule the eval job as a background task — does not block the stream."""
    from app.agents.evaluator import run_eval
    asyncio.create_task(
        run_eval(
            book_id=book_id,
            user_message=user_message,
            assistant_response=assistant_response,
            retrieved_chunks=meta.retrieved_chunks,
            tools_called=meta.tools_called,
            tool_iterations=meta.tool_iterations,
            session_id=session_id,
        )
    )


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
        session_id = payload.session_id or await create_session(book_id)

        stream: AsyncIterator[str] = _session_aware_stream(
            book_id=book_id,
            message=payload.message,
            history=history,
            session_id=session_id,
            current_page=current_page,
        )
    else:
        stream = _plain_stream(
            book_id=book_id,
            message=payload.message,
            history=history,
            current_page=current_page,
        )

    return StreamingResponse(stream, media_type="text/event-stream")
