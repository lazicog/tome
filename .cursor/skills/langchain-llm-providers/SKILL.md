---
name: langchain-llm-providers
description: >-
  Configure multi-provider LLM support using LangChain chat models (ChatOpenAI,
  ChatAnthropic, ChatOllama) with a factory pattern, async streaming, fallback
  chains, and token tracking. Use when setting up LLM calls, adding provider
  configuration, implementing streaming completions, or configuring fallback
  models in the HelpMeLearn system.
---

# LangChain Multi-Provider LLM Integration

## Installation

```bash
pip install langchain-core langchain-openai langchain-anthropic langchain-ollama
```

## Provider Factory Pattern

A single `get_chat_model()` factory returns the right `BaseChatModel` based on config. All agent code depends on `BaseChatModel`, never on a concrete provider.

```python
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama

def get_chat_model(
    provider: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> BaseChatModel:
    provider = provider or settings.llm_provider
    model = model or settings.llm_model
    temperature = temperature if temperature is not None else settings.llm_temperature
    max_tokens = max_tokens or settings.llm_max_tokens

    match provider:
        case "openai":
            return ChatOpenAI(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=settings.openai_api_key,
                streaming=True,
            )
        case "anthropic":
            return ChatAnthropic(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=settings.anthropic_api_key,
                streaming=True,
            )
        case "ollama":
            return ChatOllama(
                model=model,
                temperature=temperature,
                num_predict=max_tokens,
                base_url=settings.ollama_base_url,
            )
        case _:
            raise ValueError(f"Unsupported LLM provider: {provider}")
```

## Configuration with pydantic-settings

```python
from pydantic_settings import BaseSettings

class LLMSettings(BaseSettings):
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    llm_temperature: float = 0.3
    llm_max_tokens: int = 4096

    # Fallback config
    llm_fallback_provider: str = "anthropic"
    llm_fallback_model: str = "claude-sonnet-4-20250514"

    # API keys -- loaded from .env
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"

    # Embedding config
    embedding_provider: str = "local"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
```

## Using Chat Models in Agents

LangChain chat models use message objects and integrate natively with LangGraph:

```python
from langchain_core.messages import SystemMessage, HumanMessage

async def agent_node(state: AgentState) -> dict:
    llm = get_chat_model(temperature=0.3)
    message = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=state["query"]),
    ])
    return {"response": message.content}
```

## Streaming

LangChain chat models stream natively. Use `astream` for direct streaming or let LangGraph handle it via `astream_events`:

```python
# Direct streaming from a chat model
async def stream_response(messages: list) -> AsyncIterator[str]:
    llm = get_chat_model()
    async for chunk in llm.astream(messages):
        if chunk.content:
            yield chunk.content

# Via LangGraph (preferred -- agents stream automatically)
async for event in graph.astream_events(input_state, version="v2"):
    if event["event"] == "on_chat_model_stream":
        yield event["data"]["chunk"].content
```

## Fallback Chain

Use LangChain's `with_fallbacks()` for automatic failover:

```python
def get_chat_model_with_fallback() -> BaseChatModel:
    primary = get_chat_model(
        provider=settings.llm_provider,
        model=settings.llm_model,
    )
    fallback = get_chat_model(
        provider=settings.llm_fallback_provider,
        model=settings.llm_fallback_model,
    )
    return primary.with_fallbacks([fallback])
```

This transparently retries on the fallback model if the primary raises any exception.

## Token Tracking

Use LangChain's callback system:

```python
from langchain_core.callbacks import AsyncCallbackHandler

class TokenTracker(AsyncCallbackHandler):
    def __init__(self):
        self.prompt_tokens = 0
        self.completion_tokens = 0

    async def on_llm_end(self, response, **kwargs):
        usage = response.llm_output.get("token_usage", {})
        self.prompt_tokens += usage.get("prompt_tokens", 0)
        self.completion_tokens += usage.get("completion_tokens", 0)

# Usage
tracker = TokenTracker()
llm = get_chat_model()
result = await llm.ainvoke(messages, config={"callbacks": [tracker]})
print(f"Tokens: {tracker.prompt_tokens} in, {tracker.completion_tokens} out")
```

## LLM Service Wrapper

Centralized service used by all agents via FastAPI dependency injection:

```python
class LLMService:
    def __init__(self, settings: LLMSettings):
        self.settings = settings

    def get_model(self, temperature: float | None = None) -> BaseChatModel:
        return get_chat_model_with_fallback()

    async def complete(self, messages: list, **kwargs) -> str:
        llm = self.get_model(**kwargs)
        result = await llm.ainvoke(messages)
        return result.content
```

## .env.example Template

```bash
# LLM Configuration
LLM_PROVIDER=openai          # openai | anthropic | ollama
LLM_MODEL=gpt-4o
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=4096

# Fallback (used if primary provider fails)
LLM_FALLBACK_PROVIDER=anthropic
LLM_FALLBACK_MODEL=claude-sonnet-4-20250514

# API Keys (add the ones for your chosen provider)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Local models (Ollama)
OLLAMA_BASE_URL=http://localhost:11434

# Embeddings
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

## Provider-Specific Notes

- **OpenAI**: `ChatOpenAI` supports all OpenAI and Azure OpenAI models. Set `streaming=True` in constructor.
- **Anthropic**: `ChatAnthropic` requires `max_tokens` to be set explicitly (Anthropic API requirement).
- **Ollama**: `ChatOllama` connects to a local Ollama server. Use `num_predict` instead of `max_tokens`. Ensure the model is pulled locally (`ollama pull llama3`).
