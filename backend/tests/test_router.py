import pytest

from app.agents.graph import route_intent
from app.agents.router import classify_intent, _classify_intent_keyword, VALID_INTENTS
from app.schemas import ChatMessage


def test_classify_intent_example() -> None:
    intent = _classify_intent_keyword("Can you show me a code example for embeddings?")
    assert intent == "example"


def test_classify_intent_context() -> None:
    intent = _classify_intent_keyword("I am unfamiliar with vector databases, give me background")
    assert intent == "context"


def test_classify_intent_default_explain() -> None:
    intent = _classify_intent_keyword("Explain retrieval ranking tradeoffs")
    assert intent == "explain"


def test_classify_intent_summarize() -> None:
    intent = _classify_intent_keyword("Summarize the key concepts from this chapter")
    assert intent == "summarize"


def test_classify_intent_study_notes() -> None:
    intent = _classify_intent_keyword("Take notes on the main ideas")
    assert intent == "summarize"


def test_classify_intent_key_takeaways() -> None:
    intent = _classify_intent_keyword("What are the key takeaways?")
    assert intent == "summarize"


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("Give me a simple example of retrieval augmentation.", "example"),
        ("Can you show me a code snippet for this?", "example"),
        ("I need background before I learn this topic.", "context"),
        ("What are the prerequisites for this concept?", "context"),
        ("Explain semantic chunking tradeoffs.", "explain"),
        ("Quiz me on this chapter.", "quiz"),
        ("Test my understanding of embeddings.", "quiz"),
        ("Give me some practice questions.", "quiz"),
        ("Can you assess what I know about RAG?", "quiz"),
        ("Summarize the chapter on agents.", "summarize"),
        ("Give me a recap of this section.", "summarize"),
        ("What are the key points?", "summarize"),
    ],
)
def test_classify_intent_phrase_matrix(query: str, expected: str) -> None:
    intent = _classify_intent_keyword(query)
    assert intent == expected


def test_classify_intent_quiz() -> None:
    intent = _classify_intent_keyword("Quiz me on retrieval augmented generation.")
    assert intent == "quiz"


def test_backward_compat_classify_intent() -> None:
    """classify_intent (sync) still works for backward compat."""
    intent = classify_intent("Explain this concept", [])
    assert intent == "explain"


def test_route_intent_fallbacks() -> None:
    assert route_intent({"agent_type": "example"}) == "example_prep"
    assert route_intent({"agent_type": "context"}) == "context_prep"
    assert route_intent({"agent_type": "quiz"}) == "quiz_prep"
    assert route_intent({"agent_type": "summarize"}) == "summarize_prep"
    assert route_intent({"agent_type": "unknown"}) == "tutor_prep"


def test_valid_intents_complete() -> None:
    assert VALID_INTENTS == {"explain", "example", "context", "quiz", "summarize"}
