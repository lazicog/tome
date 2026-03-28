"""Note persistence backed by SQLite."""

import uuid
from datetime import datetime, timezone

from app.services.database import get_connection, init_db


async def create_note(
    book_id: str,
    content: str,
    *,
    page_number: int | None = None,
    chapter: str | None = None,
    title: str = "",
    note_type: str = "manual",
    source_message_id: int | None = None,
    tags: str = "",
) -> dict:
    await init_db()
    note_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    async with get_connection() as conn:
        await conn.execute(
            """INSERT INTO notes (id, book_id, page_number, chapter, title, content,
               type, source_message_id, tags, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (note_id, book_id, page_number, chapter, title, content,
             note_type, source_message_id, tags, now, now),
        )
        await conn.commit()
        cursor = await conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
        row = await cursor.fetchone()
    return dict(row)


async def get_note(note_id: str) -> dict | None:
    await init_db()
    async with get_connection() as conn:
        cursor = await conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
        row = await cursor.fetchone()
    if not row:
        return None
    return dict(row)


async def list_notes(
    book_id: str,
    *,
    page_number: int | None = None,
    note_type: str | None = None,
    search: str | None = None,
) -> list[dict]:
    await init_db()
    query = "SELECT * FROM notes WHERE book_id = ?"
    params: list = [book_id]

    if page_number is not None:
        query += " AND page_number = ?"
        params.append(page_number)
    if note_type:
        query += " AND type = ?"
        params.append(note_type)
    if search:
        query += " AND (content LIKE ? OR title LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    query += " ORDER BY created_at DESC"

    async with get_connection() as conn:
        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def update_note(
    note_id: str,
    *,
    title: str | None = None,
    content: str | None = None,
    tags: str | None = None,
) -> dict | None:
    await init_db()
    now = datetime.now(timezone.utc).isoformat()
    updates: list[str] = ["updated_at = ?"]
    params: list = [now]

    if title is not None:
        updates.append("title = ?")
        params.append(title)
    if content is not None:
        updates.append("content = ?")
        params.append(content)
    if tags is not None:
        updates.append("tags = ?")
        params.append(tags)

    params.append(note_id)

    async with get_connection() as conn:
        await conn.execute(
            f"UPDATE notes SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        await conn.commit()
        cursor = await conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
        row = await cursor.fetchone()
    if not row:
        return None
    return dict(row)


async def delete_note(note_id: str) -> bool:
    await init_db()
    async with get_connection() as conn:
        cursor = await conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        await conn.commit()
        return cursor.rowcount > 0


async def search_notes(book_id: str, query: str) -> list[dict]:
    """Full-text search across note title and content."""
    return await list_notes(book_id, search=query)
