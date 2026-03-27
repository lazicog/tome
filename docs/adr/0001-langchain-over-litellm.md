# ADR-0001: Use LangChain Chat Models over LiteLLM

**Status**: Accepted
**Date**: 2026-03-27

## Context

HelpMeLearn needs a multi-provider LLM abstraction layer to support OpenAI, Anthropic, and local models (Ollama) through a single interface. LiteLLM was the initial choice for its unified `completion()` API across providers.

However, LiteLLM was removed from consideration due to a recent security breach affecting the library. We needed an alternative that provides:
- Multi-provider support (OpenAI, Anthropic, Ollama)
- Async streaming
- Provider failover/fallback
- Native compatibility with our agent orchestration framework (LangGraph)

## Decision

Use LangChain's native chat model classes (`ChatOpenAI`, `ChatAnthropic`, `ChatOllama`) behind a factory pattern in `app/services/llm.py`. All agent code depends on the `BaseChatModel` abstract class, never on concrete provider implementations.

The factory (`get_chat_model()`) uses a `match/case` on the configured provider string to return the appropriate model instance. Fallback is handled via LangChain's built-in `with_fallbacks()` method.

## Consequences

- **Positive**: Native integration with LangGraph -- chat models work directly as LangGraph nodes without adapters
- **Positive**: `with_fallbacks()` provides automatic provider failover with zero custom code
- **Positive**: `astream_events` in LangGraph captures token-level streaming from chat models automatically
- **Positive**: No dependency on a library with known security issues
- **Negative**: Requires separate pip packages per provider (`langchain-openai`, `langchain-anthropic`, `langchain-ollama`)
- **Negative**: No single unified model string format; the factory pattern handles provider routing instead
- **Negative**: Token cost tracking requires manual callback setup rather than LiteLLM's built-in `completion_cost()`
