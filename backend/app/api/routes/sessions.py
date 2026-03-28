from fastapi import APIRouter, HTTPException

from app.schemas import ChatMessage, SessionMessagesResponse, SessionResponse
from app.services.sessions import get_messages, get_session, list_sessions

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get(
    "/book/{book_id}",
    response_model=list[SessionResponse],
    summary="List chat sessions for a book",
)
async def list_book_sessions(book_id: str) -> list[SessionResponse]:
    sessions = await list_sessions(book_id)
    result: list[SessionResponse] = []
    for s in sessions:
        msgs = await get_messages(s["id"])
        result.append(
            SessionResponse(
                id=s["id"],
                book_id=s["book_id"],
                created_at=s["created_at"],
                updated_at=s["updated_at"],
                message_count=len(msgs),
            )
        )
    return result


@router.get(
    "/{session_id}/messages",
    response_model=SessionMessagesResponse,
    summary="Get all messages in a session",
)
async def get_session_messages(session_id: str) -> SessionMessagesResponse:
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    msgs = await get_messages(session_id)
    return SessionMessagesResponse(
        session_id=session_id,
        messages=[ChatMessage(role=m["role"], content=m["content"]) for m in msgs],
    )
