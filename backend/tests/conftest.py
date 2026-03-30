"""Shared pytest fixtures for all backend tests."""

import pytest_asyncio

import app.services.database as db_mod


@pytest_asyncio.fixture
async def isolated_db(tmp_path):
    """Spin up a fresh in-memory SQLite DB for each test, pre-populated with two books."""
    db_mod._data_dir_override = tmp_path
    await db_mod.init_db()
    async with db_mod.get_connection() as conn:
        await conn.execute(
            "INSERT INTO books (id, title, file_name, status, chunks, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("book1", "Test Book 1", "test1.pdf", "ready", 10, "2026-01-01T00:00:00Z"),
        )
        await conn.execute(
            "INSERT INTO books (id, title, file_name, status, chunks, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("book2", "Test Book 2", "test2.pdf", "ready", 5, "2026-01-01T00:00:00Z"),
        )
        await conn.commit()
    yield
    db_mod._data_dir_override = None
