from app.schemas import ChatMessage


def classify_intent(query: str, _: list[ChatMessage]) -> str:
    lowered = query.lower()

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
    quiz_terms = [
        "quiz",
        "test me",
        "test my",
        "question",
        "assess",
        "check my understanding",
        "practice",
    ]
    example_terms = [
        "example",
        "sample",
        "code",
        "implement",
        "implementation",
        "snippet",
        "show me",
    ]

    if any(term in lowered for term in context_terms):
        return "context"
    if any(term in lowered for term in quiz_terms):
        return "quiz"
    if any(term in lowered for term in example_terms):
        return "example"
    return "explain"
