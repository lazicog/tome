"""Chat session and message persistence backed by SQLite."""

import uuid
from datetime import datetime, timezone

from app.services.database import get_connection, init_db


async def create_session(book_id: str) -> str:
    await init_db()
    session_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    async with get_connection() as conn:
        await conn.execute(
            "INSERT INTO chat_sessions (id, book_id, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (session_id, book_id, now, now),
        )
        await conn.commit()
    return session_id


async def get_session(session_id: str) -> dict | None:
    await init_db()
    async with get_connection() as conn:
        cursor = await conn.execute("SELECT * FROM chat_sessions WHERE id = ?", (session_id,))
        row = await cursor.fetchone()
    if not row:
        return None
    return dict(row)


async def list_sessions(book_id: str) -> list[dict]:
    await init_db()
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM chat_sessions WHERE book_id = ? ORDER BY updated_at DESC",
            (book_id,),
        )
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def add_message(
    session_id: str, role: str, content: str, agent_type: str | None = None
) -> int:
    await init_db()
    now = datetime.now(timezone.utc).isoformat()
    async with get_connection() as conn:
        cursor = await conn.execute(
            "INSERT INTO chat_messages (session_id, role, content, agent_type, created_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, role, content, agent_type, now),
        )
        await conn.execute(
            "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
            (now, session_id),
        )
        await conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]


async def get_messages(session_id: str) -> list[dict]:
    await init_db()
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        )
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]
