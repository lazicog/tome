"""Integration tests for session-aware chat and session API endpoints."""

import json
from types import SimpleNamespace

import pytest

from app.agents.tutor import _sse_event
from app.api.routes import chat as chat_route
from app.main import app
from app.schemas import ProcessingStatus
from app.services import database

from fastapi.testclient import TestClient


def _event_payloads(body: str, event_name: str) -> list[str]:
    payloads: list[str] = []
    for frame in body.split("\n\n"):
        lines = frame.splitlines()
        if not lines or lines[0] != f"event: {event_name}":
            continue
        data_lines = [line.replace("data: ", "", 1) for line in lines[1:] if line.startswith("data: ")]
        if data_lines:
            payloads.append("\n".join(data_lines))
    return payloads


def test_session_aware_chat_creates_session_and_persists(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(database, "_data_dir_override", tmp_path)

    import asyncio
    asyncio.get_event_loop().run_until_complete(database.init_db())

    from app.services.storage_db import create_book as db_create_book

    book_ref = asyncio.get_event_loop().run_until_complete(db_create_book("test.pdf"))
    book = book_ref[0]
    asyncio.get_event_loop().run_until_complete(
        __import__("app.services.storage_db", fromlist=["update_book_status"]).update_book_status(
            book.id, ProcessingStatus.ready, chunks=3
        )
    )

    async def fake_get_book(book_id: str):
        from app.services.storage_db import get_book as db_get
        return await db_get(book_id)

    async def fake_stream_routed_answer(*, book_id: str, message: str, history: list):
        _ = (book_id, message, history)
        yield _sse_event("agent", "explain")
        yield _sse_event("token", "Test response.")
        yield _sse_event("sources", [{"chunk_id": "c1", "chapter": "Ch1", "section": "S1", "page_numbers": [1], "score": 0.9}])
        yield _sse_event("done", "")

    monkeypatch.setattr(chat_route, "get_book", fake_get_book)
    monkeypatch.setattr(chat_route, "stream_routed_answer", fake_stream_routed_answer)
    monkeypatch.setattr(chat_route.settings, "phase2_routing_enabled", True)
    monkeypatch.setattr(chat_route.settings, "use_sqlite_storage", True)

    with TestClient(app) as client:
        response = client.post(
            f"/api/books/{book.id}/chat",
            json={"message": "Explain RAG.", "chat_history": []},
        )

    assert response.status_code == 200
    body = response.text

    session_payloads = _event_payloads(body, "session")
    assert len(session_payloads) == 1
    session_id = json.loads(session_payloads[0])
    assert isinstance(session_id, str)
    assert len(session_id) == 32

    assert "event: agent" in body
    assert "event: token" in body
    assert "event: sources" in body
    assert "event: done" in body


def test_session_resume_loads_history_from_db(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(database, "_data_dir_override", tmp_path)

    import asyncio
    asyncio.get_event_loop().run_until_complete(database.init_db())

    from app.services.storage_db import create_book as db_create_book
    from app.services.sessions import create_session, add_message

    book, _ = asyncio.get_event_loop().run_until_complete(db_create_book("resume.pdf"))
    asyncio.get_event_loop().run_until_complete(
        __import__("app.services.storage_db", fromlist=["update_book_status"]).update_book_status(
            book.id, ProcessingStatus.ready, chunks=2
        )
    )

    session_id = asyncio.get_event_loop().run_until_complete(create_session(book.id))
    asyncio.get_event_loop().run_until_complete(add_message(session_id, "user", "What is RAG?"))
    asyncio.get_event_loop().run_until_complete(add_message(session_id, "assistant", "RAG is...", agent_type="explain"))

    captured_history = []

    async def fake_get_book(book_id: str):
        from app.services.storage_db import get_book as db_get
        return await db_get(book_id)

    async def fake_stream_routed_answer(*, book_id: str, message: str, history: list):
        captured_history.extend(history)
        yield _sse_event("agent", "explain")
        yield _sse_event("token", "Follow-up answer.")
        yield _sse_event("sources", [])
        yield _sse_event("done", "")

    monkeypatch.setattr(chat_route, "get_book", fake_get_book)
    monkeypatch.setattr(chat_route, "stream_routed_answer", fake_stream_routed_answer)
    monkeypatch.setattr(chat_route.settings, "phase2_routing_enabled", True)
    monkeypatch.setattr(chat_route.settings, "use_sqlite_storage", True)

    with TestClient(app) as client:
        response = client.post(
            f"/api/books/{book.id}/chat",
            json={"message": "Tell me more.", "session_id": session_id},
        )

    assert response.status_code == 200
    assert len(captured_history) == 2
    assert captured_history[0].role == "user"
    assert captured_history[0].content == "What is RAG?"
    assert captured_history[1].role == "assistant"


def test_session_list_endpoint(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(database, "_data_dir_override", tmp_path)

    import asyncio
    asyncio.get_event_loop().run_until_complete(database.init_db())

    from app.services.storage_db import create_book as db_create_book
    from app.services.sessions import create_session, add_message

    book, _ = asyncio.get_event_loop().run_until_complete(db_create_book("list-test.pdf"))
    s1 = asyncio.get_event_loop().run_until_complete(create_session(book.id))
    asyncio.get_event_loop().run_until_complete(add_message(s1, "user", "Hello"))
    s2 = asyncio.get_event_loop().run_until_complete(create_session(book.id))

    with TestClient(app) as client:
        response = client.get(f"/api/sessions/book/{book.id}")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    ids = {s["id"] for s in data}
    assert s1 in ids
    assert s2 in ids
    s1_data = next(s for s in data if s["id"] == s1)
    assert s1_data["message_count"] == 1


def test_session_messages_endpoint(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(database, "_data_dir_override", tmp_path)

    import asyncio
    asyncio.get_event_loop().run_until_complete(database.init_db())

    from app.services.storage_db import create_book as db_create_book
    from app.services.sessions import create_session, add_message

    book, _ = asyncio.get_event_loop().run_until_complete(db_create_book("msg-test.pdf"))
    session_id = asyncio.get_event_loop().run_until_complete(create_session(book.id))
    asyncio.get_event_loop().run_until_complete(add_message(session_id, "user", "Question?"))
    asyncio.get_event_loop().run_until_complete(add_message(session_id, "assistant", "Answer.", agent_type="explain"))

    with TestClient(app) as client:
        response = client.get(f"/api/sessions/{session_id}/messages")

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_id
    assert len(data["messages"]) == 2
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][1]["role"] == "assistant"


def test_session_messages_404_for_missing_session(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(database, "_data_dir_override", tmp_path)

    import asyncio
    asyncio.get_event_loop().run_until_complete(database.init_db())

    with TestClient(app) as client:
        response = client.get("/api/sessions/nonexistent/messages")

    assert response.status_code == 404
    assert response.json() == {"detail": "Session not found"}
