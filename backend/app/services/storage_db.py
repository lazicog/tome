"""SQLite-backed book storage, same interface as storage.py."""

import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.schemas import BookResponse, ProcessingStatus
from app.services.database import get_connection, get_uploads_dir, init_db


def _row_to_book(row: dict) -> BookResponse:
    return BookResponse(
        id=row["id"],
        title=row["title"],
        file_name=row["file_name"],
        status=ProcessingStatus(row["status"]),
        chunks=row["chunks"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


async def create_book(file_name: str) -> tuple[BookResponse, Path]:
    await init_db()
    book_id = uuid.uuid4().hex
    uploads = get_uploads_dir()
    file_path = uploads / f"{book_id}.pdf"
    now = datetime.now(timezone.utc).isoformat()

    async with get_connection() as conn:
        await conn.execute(
            "INSERT INTO books (id, title, file_name, status, chunks, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (book_id, Path(file_name).stem, file_name, ProcessingStatus.queued.value, 0, now),
        )
        await conn.commit()
        cursor = await conn.execute("SELECT * FROM books WHERE id = ?", (book_id,))
        row = await cursor.fetchone()

    uploads.mkdir(parents=True, exist_ok=True)
    return _row_to_book(dict(row)), file_path


async def list_books(page: int = 1, limit: int = 100) -> list[BookResponse]:
    await init_db()
    offset = (page - 1) * limit
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM books ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = await cursor.fetchall()
    return [_row_to_book(dict(r)) for r in rows]


async def get_book(book_id: str) -> BookResponse | None:
    await init_db()
    async with get_connection() as conn:
        cursor = await conn.execute("SELECT * FROM books WHERE id = ?", (book_id,))
        row = await cursor.fetchone()
    if not row:
        return None
    return _row_to_book(dict(row))


async def update_book_status(book_id: str, status: ProcessingStatus, chunks: int = 0) -> None:
    await init_db()
    async with get_connection() as conn:
        if chunks:
            await conn.execute(
                "UPDATE books SET status = ?, chunks = ? WHERE id = ?",
                (status.value, chunks, book_id),
            )
        else:
            await conn.execute(
                "UPDATE books SET status = ? WHERE id = ?",
                (status.value, book_id),
            )
        await conn.commit()
