# Spec: Model Picker

**Date:** 2026-03-31
**Status:** Complete — implemented 2026-04-02
**Scope:** Frontend model selector UI + backend per-request model routing

---

## Problem

The app uses a single LLM configured at startup via `.env`. There is no way to switch models per
request. For quick questions, a fast/cheap model (GPT-4o-mini) is fine. For deep research or complex
explanations, a more capable model (Claude Opus, GPT-4o) is worth the cost. Users should be able
to make that trade-off themselves per session.

---

## Goals

1. Add a **model picker** to the chat UI — a small dropdown next to the mode selector.
2. The selected model is sent in the chat payload and used for that request only.
3. Available models are fetched from the backend so the frontend never hardcodes provider details.
4. Only models whose API key is configured are offered — no broken options.
5. The active model is remembered in `localStorage` so it persists across page reloads.

---

## Non-Goals

- Per-session model persistence in SQLite (localStorage is sufficient for now).
- Streaming model switching mid-conversation.
- Ollama model enumeration (too dynamic; Ollama users can add it manually later).
- Changing the eval model via UI.

---

## Proposed Design

### Available model list

A static list defined in the backend config, filtered at runtime to only include providers
whose API key is set:

```python
# config.py
AVAILABLE_MODELS = [
    {"id": "gpt-5.4-mini",               "label": "GPT-5.4 mini",    "provider": "openai"},
    {"id": "gpt-5.4",                    "label": "GPT-5.4",         "provider": "openai"},
    {"id": "claude-haiku-4-5-20251001",  "label": "Claude Haiku",    "provider": "anthropic"},
    {"id": "claude-sonnet-4-6",          "label": "Claude Sonnet",   "provider": "anthropic"},
    {"id": "claude-opus-4-6",            "label": "Claude Opus",     "provider": "anthropic"},
]
```

The `/api/models` endpoint returns only the entries whose provider has a configured key.
The currently-active default (from `settings.llm_model`) is marked with `"is_default": true`.

### API

**New endpoint:** `GET /api/models`

Response:
```json
{
  "models": [
    {"id": "gpt-5.4-mini",     "label": "GPT-5.4 mini",   "provider": "openai",     "is_default": true},
    {"id": "gpt-5.4",          "label": "GPT-5.4",        "provider": "openai",     "is_default": false},
    {"id": "claude-sonnet-4-6","label": "Claude Sonnet",  "provider": "anthropic",  "is_default": false}
  ],
  "default": "gpt-5.4-mini"
}
```

Only models whose provider key is non-empty are returned. If both keys are set, both providers appear.

### `ChatRequest` change

Add one optional field:

```python
model_id: str | None = None  # if None, uses settings.llm_model
```

### Orchestrator change

`stream_orchestrated_answer` receives `model_id`. If set, it calls
`get_chat_model(provider=..., model=model_id)` directly instead of `get_chat_model_with_fallback()`.

Provider is derived from model_id by matching against the AVAILABLE_MODELS list.

```python
def _resolve_model(model_id: str | None) -> BaseChatModel:
    if not model_id:
        return get_chat_model_with_fallback()
    for m in AVAILABLE_MODELS:
        if m["id"] == model_id:
            return get_chat_model(provider=m["provider"], model=model_id)
    return get_chat_model_with_fallback()  # unknown id → fall back to default
```

### Frontend UI

Location: beside the mode selector, right-aligned in the same bar.

```
[ Learn ]  [ Research ]  [ Visualize ↗ ]          [ GPT-4o mini ▾ ]
```

- A small `<select>` or custom dropdown styled to match the dark theme.
- Options fetched once on mount from `GET /api/models`.
- Selection stored in `localStorage` under key `tome_model_id`.
- On load, reads from localStorage; falls back to the server-reported default.
- The selected `model_id` is sent in every chat POST body.

### Visual indicator on messages

When a non-default model is used, show a small model badge alongside the Research badge (or instead):

```
[Claude Sonnet]   ← small sage pill, same style as Research badge
```

Only shown when the model differs from the server default. This way, default-model messages stay
clean and the badge only appears when the user made an explicit choice.

---

## File Plan

| File | Change |
|---|---|
| `backend/app/config.py` | Add `AVAILABLE_MODELS` list |
| `backend/app/api/routes/models.py` | NEW — `GET /api/models` endpoint |
| `backend/app/main.py` | Register models router |
| `backend/app/schemas.py` | Add `model_id: str | None = None` to `ChatRequest` |
| `backend/app/agents/orchestrator.py` | Add `model_id` param, `_resolve_model()`, use it instead of `get_chat_model_with_fallback()` |
| `backend/app/agents/graph.py` | Forward `model_id` |
| `backend/app/api/routes/chat.py` | Forward `payload.model_id` |
| `frontend/src/lib/api.ts` | Add `listModels()` function + `Model` type |
| `frontend/src/app/book/[bookId]/page.tsx` | Add model state (localStorage), `ModelPicker` component, pass `model_id` in chat payload, model badge on messages |
| `backend/tests/test_models_endpoint.py` | NEW — endpoint tests |

---

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| User picks Opus but has no Anthropic key | Backend filters the list — only models with a valid key are returned |
| model_id for an unknown/removed model | `_resolve_model()` falls back to default silently |
| localStorage value stale after server reconfiguration | On mount, validate selected model_id against fetched list; reset to default if not found |

---

## Test Plan

`backend/tests/test_models_endpoint.py`:
- `test_models_endpoint_returns_only_configured_providers` — only openai models when only openai key set
- `test_models_endpoint_marks_default` — default model has `is_default: true`
- `test_models_endpoint_both_providers` — both providers appear when both keys set
- `test_resolve_model_unknown_id_falls_back` — unknown model_id → uses default
- `test_chat_request_model_id_defaults_to_none` — schema default

`npm run build` — no TypeScript errors

---

## Implementation Checklist

- [ ] `config.py`: add `AVAILABLE_MODELS`
- [ ] `models.py`: new router + GET /api/models
- [ ] `main.py`: register models router
- [ ] `schemas.py`: add `model_id`
- [ ] `orchestrator.py`: `_resolve_model()`, use it
- [ ] `graph.py`: forward `model_id`
- [ ] `chat.py`: forward `model_id`
- [ ] `api.ts`: `Model` type + `listModels()`
- [ ] `page.tsx`: `ModelPicker` component, localStorage, badge
- [ ] `test_models_endpoint.py`: 5 tests
- [ ] All existing tests pass
