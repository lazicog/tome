---
name: langgraph-agents
description: >-
  Build LangGraph multi-agent workflows with StateGraph, typed state, conditional
  routing, RAG-augmented nodes, and streaming. Use when creating new agent nodes,
  defining agent graphs, implementing routing logic, or adding streaming support
  to the HelpMeLearn agent system.
---

# LangGraph Agent Patterns

## Shared State Definition

All agents share a single typed state. Nodes return partial dicts to update only their fields.

```python
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END

class AgentState(TypedDict):
    query: str
    book_id: str
    chat_history: list[dict]
    retrieved_chunks: list[dict]
    response: str
    source_chunks: list[dict]
    agent_type: str
    quiz_data: dict | None
    study_plan: dict | None
```

## Router Node Pattern

The router classifies user intent and returns the next node name. Uses the LangChain `BaseChatModel` from the shared `get_chat_model()` factory.

```python
from langchain_core.messages import SystemMessage

ROUTER_PROMPT = """Classify the user's intent into exactly one category:
- "explain": wants a concept explained
- "example": wants a code example or analogy
- "quiz": wants to be quizzed or tested
- "plan": wants a study plan or next steps
- "context": needs background on an unfamiliar term

User query: {query}
Chat history: {chat_history}

Respond with only the category name."""

async def router_node(state: AgentState) -> dict:
    llm = get_chat_model(temperature=0)
    message = await llm.ainvoke([
        SystemMessage(content=ROUTER_PROMPT.format(
            query=state["query"],
            chat_history=state["chat_history"],
        ))
    ])
    agent_type = message.content.strip().lower()
    return {"agent_type": agent_type}

def route_query(state: AgentState) -> str:
    return state["agent_type"]
```

## RAG-Augmented Agent Node Pattern

Retrieve relevant chunks, inject into prompt, generate response with LangChain chat models.

```python
from langchain_core.messages import SystemMessage

TUTOR_PROMPT = """You are a patient technical tutor. Using ONLY the context below,
explain the concept the user is asking about. Cite specific sections.

Context:
{context}

Chat history:
{chat_history}

User question: {query}"""

async def tutor_node(state: AgentState) -> dict:
    chunks = await retriever.search(
        query=state["query"],
        book_id=state["book_id"],
        k=5,
    )
    context = "\n\n".join(
        f"[{c.metadata['chapter']} > {c.metadata['section']}, p.{c.metadata['page_numbers']}]\n{c.content}"
        for c in chunks
    )

    llm = get_chat_model(temperature=0.3)
    message = await llm.ainvoke([
        SystemMessage(content=TUTOR_PROMPT.format(
            context=context,
            chat_history=state["chat_history"],
            query=state["query"],
        ))
    ])

    source_chunks = [
        {"book_id": c.metadata["book_id"], "chapter": c.metadata["chapter"],
         "section": c.metadata["section"], "page_numbers": c.metadata["page_numbers"]}
        for c in chunks
    ]
    return {"response": message.content, "retrieved_chunks": chunks, "source_chunks": source_chunks}
```

## Assembling the Graph

```python
def build_agent_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("retrieve", retrieve_node)
    graph.add_node("router", router_node)
    graph.add_node("tutor", tutor_node)
    graph.add_node("example_gen", example_gen_node)
    graph.add_node("quiz_master", quiz_master_node)
    graph.add_node("study_planner", study_planner_node)
    graph.add_node("context_enricher", context_enricher_node)

    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "router")
    graph.add_conditional_edges("router", route_query, {
        "explain": "tutor",
        "example": "example_gen",
        "quiz": "quiz_master",
        "plan": "study_planner",
        "context": "context_enricher",
    })
    for node in ["tutor", "example_gen", "quiz_master", "study_planner", "context_enricher"]:
        graph.add_edge(node, END)

    return graph.compile()
```

## Streaming to the API Layer

Use `astream_events` for token-level streaming to SSE. LangChain chat models emit `on_chat_model_stream` events natively in LangGraph:

```python
async def stream_agent_response(book_id: str, query: str, chat_history: list):
    app = build_agent_graph()
    input_state = {
        "query": query,
        "book_id": book_id,
        "chat_history": chat_history,
    }
    async for event in app.astream_events(input_state, version="v2"):
        if event["event"] == "on_chat_model_stream":
            token = event["data"]["chunk"].content
            if token:
                yield {"event": "token", "data": token}
        elif event["event"] == "on_chain_end" and event["name"] in AGENT_NODES:
            state = event["data"]["output"]
            if state.get("source_chunks"):
                yield {"event": "sources", "data": json.dumps(state["source_chunks"])}
    yield {"event": "done", "data": ""}
```

## Common Pitfalls

1. **State mutation**: never do `state["field"] = x` inside a node; return `{"field": x}` instead
2. **Missing routes**: ensure every possible router output has a matching edge, or add a fallback to "tutor"
3. **Checkpoint serialization**: all state values must be JSON-serializable if using persistence
4. **Streaming filter**: always check `event["event"]` type -- `astream_events` emits many event types
5. **Model injection**: never instantiate `ChatOpenAI()` directly in agent nodes; always use `get_chat_model()` from `app/services/llm.py`
