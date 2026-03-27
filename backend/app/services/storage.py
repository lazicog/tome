import json
import uuid
from datetime import datetime
from pathlib import Path

import aiofiles

from app.config import settings
from app.schemas import BookResponse, ProcessingStatus


async def _ensure_data_layout() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.chroma_dir.mkdir(parents=True, exist_ok=True)
    if not settings.books_index_path.exists():
        async with aiofiles.open(settings.books_index_path, "w", encoding="utf-8") as f:
            await f.write("{}")


async def load_books() -> dict[str, dict]:
    await _ensure_data_layout()
    async with aiofiles.open(settings.books_index_path, "r", encoding="utf-8") as f:
        raw = await f.read()
    return json.loads(raw or "{}")


async def save_books(books: dict[str, dict]) -> None:
    await _ensure_data_layout()
    async with aiofiles.open(settings.books_index_path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(books, indent=2))


def _to_book_response(payload: dict) -> BookResponse:
    return BookResponse(
        id=payload["id"],
        title=payload["title"],
        file_name=payload["file_name"],
        status=ProcessingStatus(payload["status"]),
        chunks=payload.get("chunks", 0),
        created_at=datetime.fromisoformat(payload["created_at"]),
    )


async def create_book(file_name: str) -> tuple[BookResponse, Path]:
    books = await load_books()
    book_id = uuid.uuid4().hex
    file_path = settings.uploads_dir / f"{book_id}.pdf"

    payload = {
        "id": book_id,
        "title": Path(file_name).stem,
        "file_name": file_name,
        "status": ProcessingStatus.queued.value,
        "chunks": 0,
        "created_at": datetime.utcnow().isoformat(),
    }
    books[book_id] = payload
    await save_books(books)
    return _to_book_response(payload), file_path


async def list_books(page: int = 1, limit: int = 100) -> list[BookResponse]:
    books = await load_books()
    items = [_to_book_response(v) for v in books.values()]
    items.sort(key=lambda x: x.created_at, reverse=True)
    start = (page - 1) * limit
    end = start + limit
    return items[start:end]


async def get_book(book_id: str) -> BookResponse | None:
    books = await load_books()
    payload = books.get(book_id)
    if not payload:
        return None
    return _to_book_response(payload)


async def update_book_status(book_id: str, status: ProcessingStatus, chunks: int = 0) -> None:
    books = await load_books()
    if book_id not in books:
        return
    books[book_id]["status"] = status.value
    if chunks:
        books[book_id]["chunks"] = chunks
    await save_books(books)
