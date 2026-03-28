from app.agents.tutor import _sse_event


def test_sse_token_event_shape() -> None:
    payload = _sse_event("token", "hello")
    assert payload.startswith("event: token\n")
    assert "data: \"hello\"\n" in payload
    assert payload.endswith("\n")


def test_sse_sources_event_shape() -> None:
    payload = _sse_event("sources", [{"chunk_id": "abc", "score": 0.9}])
    assert payload.startswith("event: sources\n")
    assert "data: [{\"chunk_id\": \"abc\", \"score\": 0.9}]\n" in payload
