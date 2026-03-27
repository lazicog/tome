# ADR-0002: Use LangGraph for Agent Orchestration

**Status**: Accepted
**Date**: 2026-03-27

## Context

HelpMeLearn requires a multi-agent system where different specialized agents (Tutor, Example Generator, Quiz Master, Study Planner, Context Enricher) are routed to based on user intent. The system needs:
- A router that classifies intent and delegates to the right agent
- Typed shared state flowing through the agent graph
- Streaming support for real-time token delivery to the frontend
- The ability to compose multi-step workflows (e.g., explain a concept then quiz on it)

Alternatives considered:
- **CrewAI**: More opinionated, role-based agent framework. Good for predefined crew workflows but less flexible for dynamic routing and custom state management.
- **AutoGen**: Multi-agent conversation framework. Better suited for agent-to-agent dialogue patterns rather than the user-facing RAG + routing pattern we need.
- **Custom orchestration**: Building routing and state management from scratch. Maximum flexibility but significant engineering effort for features that already exist.

## Decision

Use LangGraph with `StateGraph`, `TypedDict`-based state, and conditional edges for intent routing. Each agent is a node function that receives the shared state and returns a partial update dict.

The graph structure: `START -> retrieve -> router -> [tutor|example_gen|quiz_master|study_planner|context_enricher] -> END`

## Consequences

- **Positive**: `StateGraph` with `TypedDict` provides type-safe state management across all agent nodes
- **Positive**: Conditional edges map cleanly to our router pattern (classify intent -> branch to agent)
- **Positive**: `astream_events` gives token-level streaming for free when using LangChain chat models
- **Positive**: Checkpointing support for future conversation persistence
- **Positive**: Well-maintained, part of the LangChain ecosystem with active development
- **Negative**: Learning curve for the graph-based programming model (nodes, edges, state updates)
- **Negative**: All state values must be JSON-serializable if persistence/checkpointing is used
- **Negative**: Debugging multi-node graphs can be harder than linear code; requires understanding of event streams
