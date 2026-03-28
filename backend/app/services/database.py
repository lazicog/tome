from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import aiosqlite

from app.config import settings

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS books (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    file_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    chunks INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id TEXT PRIMARY KEY,
    book_id TEXT NOT NULL REFERENCES books(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES chat_sessions(id),
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    agent_type TEXT,
    created_at TEXT NOT NULL
);
"""

_data_dir_override: Path | None = None


def get_data_dir() -> Path:
    return _data_dir_override or settings.data_dir


def get_uploads_dir() -> Path:
    return get_data_dir() / "uploads"


def _db_path() -> str:
    return str(get_data_dir() / "tome.db")


@asynccontextmanager
async def get_connection() -> AsyncIterator[aiosqlite.Connection]:
    async with aiosqlite.connect(_db_path()) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA foreign_keys=ON")
        yield conn


async def init_db() -> None:
    get_data_dir().mkdir(parents=True, exist_ok=True)
    get_uploads_dir().mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(_db_path()) as conn:
        await conn.executescript(_SCHEMA_SQL)
        await conn.commit()
