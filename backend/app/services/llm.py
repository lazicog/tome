from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from app.config import settings


def get_chat_model(
    provider: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> BaseChatModel:
    chosen_provider = provider or settings.llm_provider
    chosen_model = model or settings.llm_model
    chosen_temp = settings.llm_temperature if temperature is None else temperature
    chosen_tokens = settings.llm_max_tokens if max_tokens is None else max_tokens

    match chosen_provider:
        case "openai":
            return ChatOpenAI(
                model=chosen_model,
                api_key=settings.openai_api_key or None,
                temperature=chosen_temp,
                max_tokens=chosen_tokens,
                streaming=True,
                stream_options={"include_usage": True},
            )
        case "anthropic":
            return ChatAnthropic(
                model=chosen_model,
                api_key=settings.anthropic_api_key or None,
                temperature=chosen_temp,
                max_tokens=chosen_tokens,
                streaming=True,
            )
        case "ollama":
            return ChatOllama(
                model=chosen_model,
                base_url=settings.ollama_base_url,
                temperature=chosen_temp,
                num_predict=chosen_tokens,
            )
        case _:
            raise ValueError(f"Unsupported provider: {chosen_provider}")


def get_chat_model_with_fallback() -> BaseChatModel:
    primary = get_chat_model()
    fallback = get_chat_model(
        provider=settings.llm_fallback_provider,
        model=settings.llm_fallback_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
    )
    return primary.with_fallbacks([fallback])
