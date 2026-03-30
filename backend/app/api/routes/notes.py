from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.schemas import NoteCreate, NoteResponse, NoteUpdate, SuggestTitleRequest, SuggestTitleResponse
from app.services.notes import create_note, delete_note, get_note, list_notes, update_note

router = APIRouter(tags=["notes"])


def _row_to_response(row: dict) -> NoteResponse:
    return NoteResponse(
        id=row["id"],
        book_id=row["book_id"],
        page_number=row.get("page_number"),
        chapter=row.get("chapter"),
        title=row.get("title", ""),
        content=row["content"],
        type=row["type"],
        source_message_id=row.get("source_message_id"),
        tags=row.get("tags", ""),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.post(
    "/books/{book_id}/notes",
    response_model=NoteResponse,
    status_code=201,
    summary="Create a note for a book",
)
async def create_note_endpoint(book_id: str, payload: NoteCreate) -> NoteResponse:
    valid_types = {"manual", "ai_summary", "highlight", "agent_insight"}
    if payload.type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid note type. Must be one of: {valid_types}")

    row = await create_note(
        book_id=book_id,
        content=payload.content,
        page_number=payload.page_number,
        chapter=payload.chapter,
        title=payload.title,
        note_type=payload.type,
        source_message_id=payload.source_message_id,
        tags=payload.tags,
    )
    return _row_to_response(row)


@router.get(
    "/books/{book_id}/notes",
    response_model=list[NoteResponse],
    summary="List notes for a book with optional filters",
)
async def list_notes_endpoint(
    book_id: str,
    page: int | None = Query(default=None, description="Filter by page number"),
    type: str | None = Query(default=None, description="Filter by note type"),
    search: str | None = Query(default=None, description="Search in title and content"),
) -> list[NoteResponse]:
    rows = await list_notes(book_id, page_number=page, note_type=type, search=search)
    return [_row_to_response(r) for r in rows]


@router.get(
    "/notes/{note_id}",
    response_model=NoteResponse,
    summary="Get a single note",
)
async def get_note_endpoint(note_id: str) -> NoteResponse:
    row = await get_note(note_id)
    if not row:
        raise HTTPException(status_code=404, detail="Note not found")
    return _row_to_response(row)


@router.put(
    "/notes/{note_id}",
    response_model=NoteResponse,
    summary="Update a note",
)
async def update_note_endpoint(note_id: str, payload: NoteUpdate) -> NoteResponse:
    existing = await get_note(note_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Note not found")

    row = await update_note(
        note_id,
        title=payload.title,
        content=payload.content,
        tags=payload.tags,
    )
    return _row_to_response(row)


@router.delete("/notes/{note_id}", status_code=204, summary="Delete a note")
async def delete_note_endpoint(note_id: str):
    deleted = await delete_note(note_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Note not found")
    return None


@router.post(
    "/notes/suggest-title",
    response_model=SuggestTitleResponse,
    summary="Suggest a concise title for note content using the LLM",
)
async def suggest_title_endpoint(payload: SuggestTitleRequest) -> SuggestTitleResponse:
    from app.services.llm import get_chat_model_with_fallback
    from langchain_core.messages import HumanMessage, SystemMessage

    # Truncate content to avoid blowing through tokens
    content_preview = payload.content[:2000]

    llm = get_chat_model_with_fallback()
    messages = [
        SystemMessage(
            content=(
                "You are a note-titling assistant. Generate a concise, meaningful title "
                "(5–8 words) that captures the key insight of the note. "
                "Return ONLY the title — no punctuation at the end, no quotes, nothing else."
            )
        ),
        HumanMessage(content=content_preview),
    ]
    result = await llm.ainvoke(messages)
    title = str(result.content).strip().strip('"').strip("'")
    # Truncate to 80 chars just in case
    title = title[:80]
    return SuggestTitleResponse(title=title)


@router.post(
    "/books/{book_id}/notes/generate",
    summary="AI-generate study notes for a book section",
)
async def generate_notes_endpoint(
    book_id: str,
    query: str = Query(..., description="Topic or chapter to generate notes for"),
) -> StreamingResponse:
    from app.agents.tutor import _sse_event, _format_sources, build_context
    from app.rag.retriever import search_chunks
    from app.config import settings

    SUMMARIZER_PROMPT = (
        "You are a study notes generator. Based on the retrieved book content below, "
        "create structured study notes with clear headings, key points, and examples.\n\n"
        "Context:\n{context}"
    )
    from app.services.llm import get_chat_model_with_fallback
    from app.services.notes import create_note as _create_note
    from langchain_core.messages import HumanMessage, SystemMessage

    chunks = search_chunks(book_id=book_id, query=query, k=settings.top_k_chunks)
    context = build_context(chunks)
    sources = _format_sources(chunks)

    async def _generate():
        llm = get_chat_model_with_fallback()
        messages = [
            SystemMessage(content=SUMMARIZER_PROMPT.format(context=context)),
            HumanMessage(content=f"Create study notes about: {query}"),
        ]

        yield _sse_event("agent", "summarize")

        collected = ""
        async for chunk in llm.astream(messages):
            token = chunk.content
            if token:
                collected += token
                yield _sse_event("token", token)

        if collected:
            chapter = chunks[0]["metadata"].get("chapter", "Unknown") if chunks else None
            page = chunks[0]["metadata"].get("page_numbers", [None])[0] if chunks else None
            await _create_note(
                book_id=book_id,
                content=collected,
                title=f"Notes: {query[:80]}",
                chapter=chapter,
                page_number=page,
                note_type="ai_summary",
            )
            yield _sse_event("note_saved", {"title": f"Notes: {query[:80]}"})

        yield _sse_event("sources", sources)
        yield _sse_event("done", "")

    return StreamingResponse(_generate(), media_type="text/event-stream")
