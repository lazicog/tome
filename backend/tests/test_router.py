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


def test_route_intent_fallbacks() -> None:
    assert route_intent({"agent_type": "example"}) == "example_prep"
    assert route_intent({"agent_type": "context"}) == "context_prep"
    assert route_intent({"agent_type": "unknown"}) == "tutor_prep"
