import json
import structlog

from langchain_core.messages import HumanMessage, SystemMessage

from app.schemas import ChatMessage
from app.services.llm import get_chat_model

log = structlog.get_logger()

VALID_INTENTS = {"explain", "example", "context", "quiz", "summarize"}

_ROUTER_SYSTEM = """You classify user questions about a technical book into exactly one intent.

Intents:
- explain: teach, clarify, or explain a concept from the book
- example: show code, practical demonstrations, or implementation snippets
- context: provide background knowledge or prerequisites needed to understand a topic
- quiz: test the user's understanding with questions or exercises
- summarize: create study notes, key takeaways, or condensed summaries of content

Consider the conversation history to understand follow-up questions.
Reply with ONLY valid JSON: {"intent": "<one of the five intents>"}"""


async def classify_intent_llm(query: str, history: list[ChatMessage]) -> str:
    """Use the LLM to classify intent from the query and chat history."""
    try:
        llm = get_chat_model(temperature=0, max_tokens=64)

        messages = [SystemMessage(content=_ROUTER_SYSTEM)]
        for msg in history[-4:]:
            messages.append(HumanMessage(content=msg.content) if msg.role == "user"
                            else HumanMessage(content=f"[assistant]: {msg.content[:200]}"))
        messages.append(HumanMessage(content=query))

        response = await llm.ainvoke(messages)
        text = response.content.strip()

        parsed = json.loads(text)
        intent = parsed.get("intent", "explain")
        if intent not in VALID_INTENTS:
            log.warning("router.invalid_intent", raw=intent, query=query[:80])
            return "explain"

        log.info("router.classified", intent=intent, query=query[:80])
        return intent

    except Exception as exc:
        log.warning("router.llm_fallback", error=str(exc), query=query[:80])
        return _classify_intent_keyword(query)


def _classify_intent_keyword(query: str) -> str:
    """Keyword fallback when LLM routing fails."""
    lowered = query.lower()

    context_terms = [
        "background", "context", "prerequisite", "prerequisites",
        "unfamiliar", "before i learn", "basics",
    ]
    quiz_terms = [
        "quiz", "test me", "test my", "question", "assess",
        "check my understanding", "practice",
    ]
    example_terms = [
        "example", "sample", "code", "implement", "implementation",
        "snippet", "show me",
    ]
    summarize_terms = [
        "summarize", "summary", "key takeaways", "study notes",
        "take notes", "condense", "recap", "key points", "key concepts",
    ]

    if any(term in lowered for term in context_terms):
        return "context"
    if any(term in lowered for term in quiz_terms):
        return "quiz"
    if any(term in lowered for term in summarize_terms):
        return "summarize"
    if any(term in lowered for term in example_terms):
        return "example"
    return "explain"


def classify_intent(query: str, history: list[ChatMessage]) -> str:
    """Synchronous keyword-only classifier, kept for backward-compat tests."""
    return _classify_intent_keyword(query)
