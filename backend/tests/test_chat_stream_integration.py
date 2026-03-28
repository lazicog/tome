import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.agents import graph as graph_agent
from app.agents import tutor as tutor_agent
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


def test_chat_stream_emits_routed_sse_contract(monkeypatch) -> None:
    async def fake_get_book(_: str):
        return SimpleNamespace(status=ProcessingStatus.ready)

    async def fake_stream_routed_answer(*, book_id: str, message: str, history: list):
        _ = (book_id, message, history)
        yield _sse_event("agent", "context")
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
    monkeypatch.setattr(chat_route.settings, "phase2_routing_enabled", True)

    with TestClient(app) as client:
        response = client.post(
            "/api/books/book-123/chat",
            json={"message": "Give me background first.", "chat_history": []},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    body = response.text
    agent_idx = body.index("event: agent")
    token_idx = body.index("event: token")
    sources_idx = body.index("event: sources")
    done_idx = body.index("event: done")

    assert agent_idx < token_idx < sources_idx < done_idx


def test_chat_stream_emits_fallback_tutor_sse_contract(monkeypatch) -> None:
    async def fake_get_book(_: str):
        return SimpleNamespace(status=ProcessingStatus.ready)

    async def fake_stream_tutor_answer(*, book_id: str, message: str, history: list):
        _ = (book_id, message, history)
        yield _sse_event("agent", "explain")
        yield _sse_event("token", "Tutor response.")
        yield _sse_event(
            "sources",
            [
                {
                    "chunk_id": "xyz",
                    "chapter": "Unknown",
                    "section": "Page 2",
                    "page_numbers": [2],
                    "score": 0.8,
                }
            ],
        )
        yield _sse_event("done", "")

    monkeypatch.setattr(chat_route, "get_book", fake_get_book)
    monkeypatch.setattr(chat_route, "stream_tutor_answer", fake_stream_tutor_answer)
    monkeypatch.setattr(chat_route.settings, "phase2_routing_enabled", False)

    with TestClient(app) as client:
        response = client.post(
            "/api/books/book-123/chat",
            json={"message": "Explain this briefly.", "chat_history": []},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    body = response.text
    agent_idx = body.index("event: agent")
    token_idx = body.index("event: token")
    sources_idx = body.index("event: sources")
    done_idx = body.index("event: done")

    assert agent_idx < token_idx < sources_idx < done_idx


def test_upload_to_ready_to_routed_chat_flow(monkeypatch, tmp_path) -> None:
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
        _ = file_path
        existing = books[book_id]
        books[book_id] = existing.model_copy(update={"status": ProcessingStatus.ready, "chunks": 3})

    async def fake_stream_routed_answer(*, book_id: str, message: str, history: list):
        _ = (book_id, message, history)
        yield _sse_event("agent", "context")
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
    monkeypatch.setattr(chat_route.settings, "phase2_routing_enabled", True)

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
    assert body.index("event: agent") < body.index("event: token") < body.index("event: sources") < body.index("event: done")


@pytest.mark.parametrize(
    ("message", "expected_agent"),
    [
        ("Explain semantic chunking simply.", "explain"),
        ("Show me a code example for embeddings.", "example"),
        ("I am unfamiliar with cosine similarity, give me background first.", "context"),
    ],
)
def test_chat_stream_routes_expected_agent_intent(monkeypatch, message: str, expected_agent: str) -> None:
    async def fake_get_book(_: str):
        return SimpleNamespace(status=ProcessingStatus.ready)

    def fake_search_chunks(*, book_id: str, query: str, k: int):
        _ = (book_id, query, k)
        return [
            {
                "id": "chunk-1",
                "content": "Vector embeddings are numeric representations.",
                "metadata": {"chapter": "Unknown", "section": "Page 1", "page_numbers": [1]},
                "score": 0.9,
            }
        ]

    class FakeModel:
        async def astream(self, _messages):
            yield SimpleNamespace(content="stub-response")

    def fake_llm():
        return FakeModel()

    monkeypatch.setattr(chat_route, "get_book", fake_get_book)
    monkeypatch.setattr(graph_agent, "search_chunks", fake_search_chunks)
    monkeypatch.setattr(tutor_agent, "get_chat_model_with_fallback", fake_llm)
    monkeypatch.setattr(chat_route.settings, "phase2_routing_enabled", True)

    with TestClient(app) as client:
        response = client.post(
            "/api/books/book-123/chat",
            json={"message": message, "chat_history": []},
        )

    assert response.status_code == 200
    body = response.text
    assert f'data: "{expected_agent}"' in body
    assert body.count("event: sources") == 1
    source_payloads = _event_payloads(body, "sources")
    assert len(source_payloads) == 1
    sources = json.loads(source_payloads[0])
    assert isinstance(sources, list)
    assert len(sources) == 1
    source = sources[0]
    assert set(source.keys()) == {"chunk_id", "chapter", "section", "page_numbers", "score"}
    assert isinstance(source["page_numbers"], list)
    assert body.index("event: agent") < body.index("event: token") < body.index("event: sources") < body.index("event: done")
