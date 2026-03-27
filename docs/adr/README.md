# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) for HelpMeLearn. ADRs capture the **why** behind significant design choices so future-you (or contributors) can understand the reasoning.

## When to Write an ADR

- Choosing a library, framework, or tool
- Picking an architecture or design pattern
- Making a data model decision
- Changing or reversing a previous decision

## Template

```markdown
# ADR-NNNN: Title

**Status**: Proposed | Accepted | Deprecated | Superseded by ADR-XXXX
**Date**: YYYY-MM-DD

## Context
What is the issue or question? What constraints exist?

## Decision
What did we decide? Be specific.

## Consequences
What are the trade-offs? List both positives and negatives.
```

## Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [0001](0001-langchain-over-litellm.md) | Use LangChain Chat Models over LiteLLM | Accepted | 2026-03-27 |
| [0002](0002-langgraph-for-orchestration.md) | Use LangGraph for Agent Orchestration | Accepted | 2026-03-27 |
| [0003](0003-phase1-local-storage-and-sse.md) | Phase 1 uses local metadata storage and SSE chat streaming | Accepted | 2026-03-27 |
