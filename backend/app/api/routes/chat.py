from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.agents.graph import stream_routed_answer
from app.agents.tutor import stream_tutor_answer
from app.config import settings
from app.schemas import ChatRequest, ProcessingStatus
from app.services.storage import get_book

router = APIRouter(prefix="/books", tags=["chat"])


@router.post("/{book_id}/chat", summary="Chat with a processed book")
async def chat_with_book(book_id: str, payload: ChatRequest) -> StreamingResponse:
    book = await get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if book.status != ProcessingStatus.ready:
        raise HTTPException(status_code=400, detail="Book is still processing")

    if settings.phase2_routing_enabled:
        stream = stream_routed_answer(book_id=book_id, message=payload.message, history=payload.chat_history)
    else:
        stream = stream_tutor_answer(book_id=book_id, message=payload.message, history=payload.chat_history)
    return StreamingResponse(stream, media_type="text/event-stream")
