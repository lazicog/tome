import pytest

from app.agents.graph import route_intent
from app.agents.router import classify_intent
from app.schemas import ChatMessage


def test_classify_intent_example() -> None:
    intent = classify_intent("Can you show me a code example for embeddings?", [])
    assert intent == "example"


def test_classify_intent_context() -> None:
    intent = classify_intent("I am unfamiliar with vector databases, give me background", [])
    assert intent == "context"


def test_classify_intent_default_explain() -> None:
    intent = classify_intent("Explain retrieval ranking tradeoffs", [ChatMessage(role="user", content="Hi")])
    assert intent == "explain"


def test_classify_intent_ignores_history_for_routing() -> None:
    history = [ChatMessage(role="user", content="Show me a code example of embeddings.")]
    intent = classify_intent("I am unfamiliar with cosine similarity, give me background first.", history)
    assert intent == "context"


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("Give me a simple example of retrieval augmentation.", "example"),
        ("Can you show me a code snippet for this?", "example"),
        ("I need background before I learn this topic.", "context"),
        ("What are the prerequisites for this concept?", "context"),
        ("Explain semantic chunking tradeoffs.", "explain"),
    ],
)
def test_classify_intent_phrase_matrix(query: str, expected: str) -> None:
    intent = classify_intent(query, [])
    assert intent == expected


def test_route_intent_fallbacks() -> None:
    assert route_intent({"agent_type": "example"}) == "example_prep"
    assert route_intent({"agent_type": "context"}) == "context_prep"
    assert route_intent({"agent_type": "unknown"}) == "tutor_prep"
