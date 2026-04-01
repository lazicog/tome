from fastapi import APIRouter

from app.config import AVAILABLE_MODELS, settings

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", summary="List available LLM models")
def list_models() -> dict:
    """Return models filtered to those whose provider API key is configured."""
    has_openai = bool(settings.openai_api_key)
    has_anthropic = bool(settings.anthropic_api_key)

    models = []
    for m in AVAILABLE_MODELS:
        if m["provider"] == "openai" and not has_openai:
            continue
        if m["provider"] == "anthropic" and not has_anthropic:
            continue
        models.append({
            **m,
            "is_default": m["id"] == settings.llm_model,
        })

    return {
        "models": models,
        "default": settings.llm_model,
    }
