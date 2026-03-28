from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.context_enricher import CONTEXT_PROMPT
from app.agents.example_gen import EXAMPLE_PROMPT
from app.agents.router import classify_intent
from app.config import settings
from app.agents.tutor import TUTOR_PROMPT, _format_sources, build_context, stream_prompted_answer
from app.rag.retriever import search_chunks
from app.schemas import ChatMessage


class AgentState(TypedDict, total=False):
    query: str
    book_id: str
    chat_history: list[ChatMessage]
    retrieved_chunks: list[dict]
    agent_type: str
    response: str
    source_chunks: list[dict]
    context: str
    system_prompt: str


async def retrieve_node(state: AgentState) -> dict:
    chunks = search_chunks(book_id=state["book_id"], query=state["query"], k=settings.top_k_chunks)
    return {
        "retrieved_chunks": chunks,
        "source_chunks": _format_sources(chunks),
        "context": build_context(chunks),
    }


async def router_node(state: AgentState) -> dict:
    agent_type = classify_intent(state["query"], state.get("chat_history", []))
    return {"agent_type": agent_type}


def route_intent(state: AgentState) -> Literal["tutor_prep", "example_prep", "context_prep"]:
    intent = state.get("agent_type", "explain")
    if intent == "example":
        return "example_prep"
    if intent == "context":
        return "context_prep"
    return "tutor_prep"


async def tutor_prep_node(_: AgentState) -> dict:
    return {"system_prompt": TUTOR_PROMPT}


async def example_prep_node(_: AgentState) -> dict:
    return {"system_prompt": EXAMPLE_PROMPT}


async def context_prep_node(_: AgentState) -> dict:
    return {"system_prompt": CONTEXT_PROMPT}


def build_phase2_graph():
    graph = StateGraph(AgentState)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("router", router_node)
    graph.add_node("tutor_prep", tutor_prep_node)
    graph.add_node("example_prep", example_prep_node)
    graph.add_node("context_prep", context_prep_node)

    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "router")
    graph.add_conditional_edges(
        "router",
        route_intent,
        {
            "tutor_prep": "tutor_prep",
            "example_prep": "example_prep",
            "context_prep": "context_prep",
        },
    )
    graph.add_edge("tutor_prep", END)
    graph.add_edge("example_prep", END)
    graph.add_edge("context_prep", END)
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
    ):
        yield event
