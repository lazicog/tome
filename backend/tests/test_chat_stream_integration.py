import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.agents.tutor import _sse_event
from app.api.routes import books as books_route
from app.api.routes import chat as chat_route
from app.main import app
from app.schemas import BookResponse, ProcessingStatus


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


def test_chat_stream_emits_sse_contract(monkeypatch) -> None:
    """Orchestrator path: token → sources → done in order."""
    async def fake_get_book(_: str):
        return SimpleNamespace(status=ProcessingStatus.ready)

    async def fake_stream_routed_answer(*, book_id: str, message: str, history: list, current_page=None, mode="learn"):
        yield _sse_event("token", "Background first.")
        yield _sse_event(
            "sources",
            [
                {
                    "chunk_id": "abc",
                    "chapter": "Unknown",
                    "section": "Page 1",
                    "page_numbers": [1],
                    "score": 0.9,
                }
            ],
        )
        yield _sse_event("done", "")

    monkeypatch.setattr(chat_route, "get_book", fake_get_book)
    monkeypatch.setattr(chat_route, "stream_routed_answer", fake_stream_routed_answer)
    monkeypatch.setattr(chat_route.settings, "use_sqlite_storage", False)

    with TestClient(app) as client:
        response = client.post(
            "/api/books/book-123/chat",
            json={"message": "Give me background first.", "chat_history": []},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    body = response.text
    token_idx = body.index("event: token")
    sources_idx = body.index("event: sources")
    done_idx = body.index("event: done")

    assert token_idx < sources_idx < done_idx


def test_chat_stream_thinking_event_passes_through(monkeypatch) -> None:
    """thinking SSE events (tool-use labels) are forwarded to the client."""
    async def fake_get_book(_: str):
        return SimpleNamespace(status=ProcessingStatus.ready)

    async def fake_stream_routed_answer(*, book_id: str, message: str, history: list, current_page=None, mode="learn"):
        yield _sse_event("thinking", "Searching book…")
        yield _sse_event("token", "Here is what I found.")
        yield _sse_event("sources", [])
        yield _sse_event("done", "")

    monkeypatch.setattr(chat_route, "get_book", fake_get_book)
    monkeypatch.setattr(chat_route, "stream_routed_answer", fake_stream_routed_answer)
    monkeypatch.setattr(chat_route.settings, "use_sqlite_storage", False)

    with TestClient(app) as client:
        response = client.post(
            "/api/books/book-123/chat",
            json={"message": "Explain this.", "chat_history": []},
        )

    assert response.status_code == 200
    body = response.text
    assert "event: thinking" in body
    thinking_payloads = _event_payloads(body, "thinking")
    assert len(thinking_payloads) == 1
    assert json.loads(thinking_payloads[0]) == "Searching book…"


def test_chat_returns_404_when_book_missing(monkeypatch) -> None:
    async def fake_get_book(_: str):
        return None

    monkeypatch.setattr(chat_route, "get_book", fake_get_book)

    with TestClient(app) as client:
        response = client.post(
            "/api/books/nonexistent-id/chat",
            json={"message": "Hello.", "chat_history": []},
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "Book not found"}


@pytest.mark.parametrize("status", [ProcessingStatus.queued, ProcessingStatus.processing, ProcessingStatus.failed])
def test_chat_returns_400_when_book_not_ready(monkeypatch, status: ProcessingStatus) -> None:
    async def fake_get_book(_: str):
        return SimpleNamespace(status=status)

    monkeypatch.setattr(chat_route, "get_book", fake_get_book)

    with TestClient(app) as client:
        response = client.post(
            "/api/books/book-123/chat",
            json={"message": "Hello.", "chat_history": []},
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "Book is still processing"}


def test_upload_to_ready_to_chat_flow(monkeypatch, tmp_path) -> None:
    books: dict[str, BookResponse] = {}

    async def fake_create_book(file_name: str):
        book = BookResponse(
            id="book-integration-1",
            title=Path(file_name).stem,
            file_name=file_name,
            status=ProcessingStatus.queued,
            chunks=0,
            created_at=datetime.now(timezone.utc),
        )
        books[book.id] = book
        return book, tmp_path / f"{book.id}.pdf"

    async def fake_get_book(book_id: str):
        return books.get(book_id)

    async def fake_process_book(book_id: str, file_path: str) -> None:
        existing = books[book_id]
        books[book_id] = existing.model_copy(update={"status": ProcessingStatus.ready, "chunks": 3})

    async def fake_stream_routed_answer(*, book_id: str, message: str, history: list, current_page=None, mode="learn"):
        yield _sse_event("token", "Routed response.")
        yield _sse_event(
            "sources",
            [
                {
                    "chunk_id": "source-1",
                    "chapter": "Unknown",
                    "section": "Page 1",
                    "page_numbers": [1],
                    "score": 0.7,
                }
            ],
        )
        yield _sse_event("done", "")

    monkeypatch.setattr(books_route, "create_book", fake_create_book)
    monkeypatch.setattr(books_route, "get_book", fake_get_book)
    monkeypatch.setattr(books_route, "_process_book", fake_process_book)
    monkeypatch.setattr(chat_route, "get_book", fake_get_book)
    monkeypatch.setattr(chat_route, "stream_routed_answer", fake_stream_routed_answer)
    monkeypatch.setattr(chat_route.settings, "use_sqlite_storage", False)

    with TestClient(app) as client:
        upload = client.post(
            "/api/books",
            files={"file": ("mini.pdf", b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n", "application/pdf")},
        )
        assert upload.status_code == 201
        book_id = upload.json()["id"]

        book = client.get(f"/api/books/{book_id}")
        assert book.status_code == 200
        assert book.json()["status"] == "ready"

        chat = client.post(
            f"/api/books/{book_id}/chat",
            json={"message": "Give me background first.", "chat_history": []},
        )

    assert chat.status_code == 200
    assert chat.headers["content-type"].startswith("text/event-stream")
    body = chat.text
    assert body.index("event: token") < body.index("event: sources") < body.index("event: done")


def test_chat_sends_current_page_when_provided(monkeypatch) -> None:
    """current_page in POST body is forwarded to stream_routed_answer."""
    async def fake_get_book(_: str):
        return SimpleNamespace(status=ProcessingStatus.ready)

    captured: dict = {}

    async def fake_stream_routed_answer(*, book_id: str, message: str, history: list, current_page=None, mode="learn"):
        captured["current_page"] = current_page
        yield _sse_event("token", "ok")
        yield _sse_event("sources", [])
        yield _sse_event("done", "")

    monkeypatch.setattr(chat_route, "get_book", fake_get_book)
    monkeypatch.setattr(chat_route, "stream_routed_answer", fake_stream_routed_answer)
    monkeypatch.setattr(chat_route.settings, "use_sqlite_storage", False)

    with TestClient(app) as client:
        client.post(
            "/api/books/book-123/chat",
            json={"message": "What is this?", "chat_history": [], "current_page": 5},
        )

    assert captured.get("current_page") == 5


def test_chat_omits_current_page_defaults_to_none(monkeypatch) -> None:
    """When current_page is omitted from POST body, stream_routed_answer receives None."""
    async def fake_get_book(_: str):
        return SimpleNamespace(status=ProcessingStatus.ready)

    captured: dict = {}

    async def fake_stream_routed_answer(*, book_id: str, message: str, history: list, current_page=None, mode="learn"):
        captured["current_page"] = current_page
        yield _sse_event("token", "ok")
        yield _sse_event("sources", [])
        yield _sse_event("done", "")

    monkeypatch.setattr(chat_route, "get_book", fake_get_book)
    monkeypatch.setattr(chat_route, "stream_routed_answer", fake_stream_routed_answer)
    monkeypatch.setattr(chat_route.settings, "use_sqlite_storage", False)

    with TestClient(app) as client:
        client.post(
            "/api/books/book-123/chat",
            json={"message": "What is this?", "chat_history": []},
        )

    assert captured.get("current_page") is None
