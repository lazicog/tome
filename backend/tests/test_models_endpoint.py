"""Tests for GET /api/models endpoint."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_models_returns_200():
    res = client.get("/api/models")
    assert res.status_code == 200


def test_models_response_shape():
    res = client.get("/api/models")
    data = res.json()
    assert "models" in data
    assert "default" in data
    assert isinstance(data["models"], list)


def test_models_each_has_required_fields(monkeypatch):
    monkeypatch.setattr("app.config.settings.openai_api_key", "sk-test")
    monkeypatch.setattr("app.config.settings.anthropic_api_key", "")
    res = client.get("/api/models")
    for m in res.json()["models"]:
        assert "id" in m
        assert "label" in m
        assert "provider" in m
        assert "is_default" in m


def test_models_filtered_by_openai_key(monkeypatch):
    monkeypatch.setattr("app.config.settings.openai_api_key", "sk-test")
    monkeypatch.setattr("app.config.settings.anthropic_api_key", "")
    res = client.get("/api/models")
    models = res.json()["models"]
    providers = {m["provider"] for m in models}
    assert "openai" in providers
    assert "anthropic" not in providers


def test_models_filtered_by_anthropic_key(monkeypatch):
    monkeypatch.setattr("app.config.settings.openai_api_key", "")
    monkeypatch.setattr("app.config.settings.anthropic_api_key", "sk-ant-test")
    res = client.get("/api/models")
    models = res.json()["models"]
    providers = {m["provider"] for m in models}
    assert "anthropic" in providers
    assert "openai" not in providers


def test_models_default_marked(monkeypatch):
    monkeypatch.setattr("app.config.settings.openai_api_key", "sk-test")
    monkeypatch.setattr("app.config.settings.anthropic_api_key", "sk-ant-test")
    res = client.get("/api/models")
    data = res.json()
    default_id = data["default"]
    defaults = [m for m in data["models"] if m["is_default"]]
    # At most one model should be marked as default
    assert len(defaults) <= 1
    if defaults:
        assert defaults[0]["id"] == default_id
