from app.schemas import ChatMessage


def classify_intent(query: str, history: list[ChatMessage]) -> str:
    text = f"{query} " + " ".join(m.content for m in history[-3:])
    lowered = text.lower()

    example_terms = [
        "example",
        "sample",
        "code",
        "implement",
        "implementation",
        "snippet",
        "show me",
    ]
    context_terms = [
        "background",
        "context",
        "prerequisite",
        "prerequisites",
        "unfamiliar",
        "before i learn",
        "what is",
        "basics",
    ]

    if any(term in lowered for term in example_terms):
        return "example"
    if any(term in lowered for term in context_terms):
        return "context"
    return "explain"
