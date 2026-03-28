from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.context_enricher import CONTEXT_PROMPT
from app.agents.example_gen import EXAMPLE_PROMPT
from app.agents.quiz_master import QUIZ_PROMPT
from app.agents.router import classify_intent_llm
from app.agents.summarizer import SUMMARIZER_PROMPT
from app.config import settings
from app.agents.tutor import TUTOR_PROMPT, _format_sources, build_context, stream_prompted_answer
from app.rag.retriever import search_chunks
from app.schemas import ChatMessage


class AgentState(TypedDict, total=False):
    query: str
    book_id: str
    chat_history: list[ChatMessage]
    search_queries: list[str]
    retrieved_chunks: list[dict]
    agent_type: str
    response: str
    source_chunks: list[dict]
    context: str
    system_prompt: str


async def router_node(state: AgentState) -> dict:
    agent_type = await classify_intent_llm(state["query"], state.get("chat_history", []))
    return {"agent_type": agent_type}


async def query_rewrite_node(state: AgentState) -> dict:
    """Rewrite the user query into better search queries using the LLM."""
    if not settings.query_rewrite_enabled:
        return {"search_queries": [state["query"]]}

    from langchain_core.messages import HumanMessage, SystemMessage
    from app.services.llm import get_chat_model

    rewrite_prompt = (
        "You help rewrite user questions into 2-3 search queries optimized for "
        "semantic search over a technical book. Consider the conversation context.\n"
        "Reply with ONLY a JSON array of strings, e.g. [\"query1\", \"query2\"]"
    )

    try:
        llm = get_chat_model(temperature=0, max_tokens=256)
        messages = [SystemMessage(content=rewrite_prompt)]

        history = state.get("chat_history", [])
        for msg in history[-4:]:
            messages.append(HumanMessage(content=msg.content if msg.role == "user"
                                          else f"[assistant]: {msg.content[:200]}"))
        messages.append(HumanMessage(content=state["query"]))

        import json, structlog
        log = structlog.get_logger()

        response = await llm.ainvoke(messages)
        queries = json.loads(response.content.strip())
        if isinstance(queries, list) and all(isinstance(q, str) for q in queries):
            log.info("query_rewrite.success", original=state["query"][:80], rewritten=len(queries))
            return {"search_queries": queries}
    except Exception as exc:
        import structlog
        structlog.get_logger().warning("query_rewrite.fallback", error=str(exc))

    return {"search_queries": [state["query"]]}


async def retrieve_node(state: AgentState) -> dict:
    queries = state.get("search_queries", [state["query"]])
    all_chunks: dict[str, dict] = {}

    for q in queries:
        chunks = search_chunks(book_id=state["book_id"], query=q, k=settings.top_k_chunks)
        for c in chunks:
            if c["id"] not in all_chunks or c["score"] > all_chunks[c["id"]]["score"]:
                all_chunks[c["id"]] = c

    merged = sorted(all_chunks.values(), key=lambda x: x["score"], reverse=True)
    top_chunks = merged[:settings.top_k_chunks]

    return {
        "retrieved_chunks": top_chunks,
        "source_chunks": _format_sources(top_chunks),
        "context": build_context(top_chunks),
    }


def route_intent(state: AgentState) -> Literal[
    "tutor_prep", "example_prep", "context_prep", "quiz_prep", "summarize_prep"
]:
    intent = state.get("agent_type", "explain")
    if intent == "example":
        return "example_prep"
    if intent == "context":
        return "context_prep"
    if intent == "quiz":
        return "quiz_prep"
    if intent == "summarize":
        return "summarize_prep"
    return "tutor_prep"


async def tutor_prep_node(_: AgentState) -> dict:
    return {"system_prompt": TUTOR_PROMPT}


async def example_prep_node(_: AgentState) -> dict:
    return {"system_prompt": EXAMPLE_PROMPT}


async def context_prep_node(_: AgentState) -> dict:
    return {"system_prompt": CONTEXT_PROMPT}


async def quiz_prep_node(_: AgentState) -> dict:
    return {"system_prompt": QUIZ_PROMPT}


async def summarize_prep_node(_: AgentState) -> dict:
    return {"system_prompt": SUMMARIZER_PROMPT}


def build_phase2_graph():
    graph = StateGraph(AgentState)
    graph.add_node("router", router_node)
    graph.add_node("query_rewrite", query_rewrite_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("tutor_prep", tutor_prep_node)
    graph.add_node("example_prep", example_prep_node)
    graph.add_node("context_prep", context_prep_node)
    graph.add_node("quiz_prep", quiz_prep_node)
    graph.add_node("summarize_prep", summarize_prep_node)

    graph.add_edge(START, "router")
    graph.add_edge("router", "query_rewrite")
    graph.add_edge("query_rewrite", "retrieve")
    graph.add_conditional_edges(
        "retrieve",
        route_intent,
        {
            "tutor_prep": "tutor_prep",
            "example_prep": "example_prep",
            "context_prep": "context_prep",
            "quiz_prep": "quiz_prep",
            "summarize_prep": "summarize_prep",
        },
    )
    graph.add_edge("tutor_prep", END)
    graph.add_edge("example_prep", END)
    graph.add_edge("context_prep", END)
    graph.add_edge("quiz_prep", END)
    graph.add_edge("summarize_prep", END)
    return graph.compile()


async def stream_routed_answer(book_id: str, message: str, history: list[ChatMessage]):
    app = build_phase2_graph()
    state = await app.ainvoke(
        {
            "query": message,
            "book_id": book_id,
            "chat_history": history,
        }
    )
    async for event in stream_prompted_answer(
        system_prompt=state["system_prompt"],
        context=state.get("context", ""),
        message=message,
        history=history,
        sources=state.get("source_chunks", []),
        agent_type=state.get("agent_type", "explain"),
    ):
        yield event
