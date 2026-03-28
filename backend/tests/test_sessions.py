import pytest
import pytest_asyncio

from app.services import database


@pytest_asyncio.fixture
async def _fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "_data_dir_override", tmp_path)
    await database.init_db()


@pytest_asyncio.fixture
async def book_id(_fresh_db):
    """Create a book and return its id for session tests."""
    from app.services.storage_db import create_book

    book, _ = await create_book("session-test.pdf")
    return book.id


@pytest.mark.asyncio
async def test_create_and_get_session(book_id):
    from app.services.sessions import create_session, get_session

    session_id = await create_session(book_id)
    assert isinstance(session_id, str)
    assert len(session_id) == 32

    session = await get_session(session_id)
    assert session is not None
    assert session["book_id"] == book_id


@pytest.mark.asyncio
async def test_get_nonexistent_session(_fresh_db):
    from app.services.sessions import get_session

    result = await get_session("does-not-exist")
    assert result is None


@pytest.mark.asyncio
async def test_list_sessions(book_id):
    from app.services.sessions import create_session, list_sessions

    await create_session(book_id)
    await create_session(book_id)

    sessions = await list_sessions(book_id)
    assert len(sessions) == 2
    assert all(s["book_id"] == book_id for s in sessions)


@pytest.mark.asyncio
async def test_add_and_get_messages(book_id):
    from app.services.sessions import add_message, create_session, get_messages

    session_id = await create_session(book_id)

    msg1_id = await add_message(session_id, "user", "What is RAG?")
    msg2_id = await add_message(session_id, "assistant", "RAG stands for...", agent_type="explain")

    assert isinstance(msg1_id, int)
    assert msg2_id > msg1_id

    messages = await get_messages(session_id)
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "What is RAG?"
    assert messages[0]["agent_type"] is None
    assert messages[1]["role"] == "assistant"
    assert messages[1]["agent_type"] == "explain"


@pytest.mark.asyncio
async def test_empty_session_messages(book_id):
    from app.services.sessions import create_session, get_messages

    session_id = await create_session(book_id)
    messages = await get_messages(session_id)
    assert messages == []


@pytest.mark.asyncio
async def test_add_message_updates_session_timestamp(book_id):
    from app.services.sessions import add_message, create_session, get_session

    session_id = await create_session(book_id)
    session_before = await get_session(session_id)
    assert session_before is not None

    await add_message(session_id, "user", "Hello")
    session_after = await get_session(session_id)
    assert session_after is not None
    assert session_after["updated_at"] >= session_before["updated_at"]
