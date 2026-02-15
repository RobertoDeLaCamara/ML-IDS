"""Tests for API Key authentication middleware."""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from src.inference_server.auth import APIKeyMiddleware, get_api_keys, is_auth_enabled, verify_ws_api_key


def _make_app(env_vars: dict = None):
    """Create a minimal FastAPI app with auth middleware for testing."""
    app = FastAPI()
    app.add_middleware(APIKeyMiddleware)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/predict")
    async def predict():
        return {"prediction": [0]}

    @app.get("/")
    async def root():
        return {"message": "root"}

    return app


class TestGetApiKeys:
    def test_empty(self, monkeypatch):
        monkeypatch.delenv("ML_IDS_API_KEYS", raising=False)
        assert get_api_keys() == []

    def test_single_key(self, monkeypatch):
        monkeypatch.setenv("ML_IDS_API_KEYS", "key1")
        assert get_api_keys() == ["key1"]

    def test_multiple_keys(self, monkeypatch):
        monkeypatch.setenv("ML_IDS_API_KEYS", "key1,key2,key3")
        assert get_api_keys() == ["key1", "key2", "key3"]

    def test_strips_whitespace(self, monkeypatch):
        monkeypatch.setenv("ML_IDS_API_KEYS", " key1 , key2 ")
        assert get_api_keys() == ["key1", "key2"]


class TestIsAuthEnabled:
    def test_default_true(self, monkeypatch):
        monkeypatch.delenv("ML_IDS_AUTH_ENABLED", raising=False)
        assert is_auth_enabled() is True

    def test_false(self, monkeypatch):
        monkeypatch.setenv("ML_IDS_AUTH_ENABLED", "false")
        assert is_auth_enabled() is False


class TestMiddleware:
    def test_unauthenticated_returns_401(self, monkeypatch):
        monkeypatch.setenv("ML_IDS_AUTH_ENABLED", "true")
        monkeypatch.setenv("ML_IDS_API_KEYS", "secret-key")
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/predict")
        assert resp.status_code == 401

    def test_valid_key_succeeds(self, monkeypatch):
        monkeypatch.setenv("ML_IDS_AUTH_ENABLED", "true")
        monkeypatch.setenv("ML_IDS_API_KEYS", "secret-key")
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/predict", headers={"X-API-Key": "secret-key"})
        assert resp.status_code == 200

    def test_invalid_key_returns_401(self, monkeypatch):
        monkeypatch.setenv("ML_IDS_AUTH_ENABLED", "true")
        monkeypatch.setenv("ML_IDS_API_KEYS", "secret-key")
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/predict", headers={"X-API-Key": "wrong-key"})
        assert resp.status_code == 401

    def test_health_bypasses_auth(self, monkeypatch):
        monkeypatch.setenv("ML_IDS_AUTH_ENABLED", "true")
        monkeypatch.setenv("ML_IDS_API_KEYS", "secret-key")
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_root_bypasses_auth(self, monkeypatch):
        monkeypatch.setenv("ML_IDS_AUTH_ENABLED", "true")
        monkeypatch.setenv("ML_IDS_API_KEYS", "secret-key")
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/")
        assert resp.status_code == 200

    def test_auth_disabled(self, monkeypatch):
        monkeypatch.setenv("ML_IDS_AUTH_ENABLED", "false")
        monkeypatch.setenv("ML_IDS_API_KEYS", "secret-key")
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/predict")
        assert resp.status_code == 200

    def test_no_keys_configured_allows_request(self, monkeypatch):
        monkeypatch.setenv("ML_IDS_AUTH_ENABLED", "true")
        monkeypatch.delenv("ML_IDS_API_KEYS", raising=False)
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/predict")
        assert resp.status_code == 200


class TestWebSocketAuth:
    @pytest.mark.asyncio
    async def test_ws_auth_disabled(self, monkeypatch):
        monkeypatch.setenv("ML_IDS_AUTH_ENABLED", "false")
        ws = MagicMock()
        assert await verify_ws_api_key(ws) is True

    @pytest.mark.asyncio
    async def test_ws_no_keys_allows(self, monkeypatch):
        monkeypatch.setenv("ML_IDS_AUTH_ENABLED", "true")
        monkeypatch.delenv("ML_IDS_API_KEYS", raising=False)
        ws = MagicMock()
        assert await verify_ws_api_key(ws) is True

    @pytest.mark.asyncio
    async def test_ws_valid_key(self, monkeypatch):
        monkeypatch.setenv("ML_IDS_AUTH_ENABLED", "true")
        monkeypatch.setenv("ML_IDS_API_KEYS", "ws-key")
        ws = MagicMock()
        ws.query_params = {"api_key": "ws-key"}
        assert await verify_ws_api_key(ws) is True

    @pytest.mark.asyncio
    async def test_ws_invalid_key(self, monkeypatch):
        monkeypatch.setenv("ML_IDS_AUTH_ENABLED", "true")
        monkeypatch.setenv("ML_IDS_API_KEYS", "ws-key")
        ws = MagicMock()
        ws.query_params = {"api_key": "wrong"}
        assert await verify_ws_api_key(ws) is False

    @pytest.mark.asyncio
    async def test_ws_missing_key(self, monkeypatch):
        monkeypatch.setenv("ML_IDS_AUTH_ENABLED", "true")
        monkeypatch.setenv("ML_IDS_API_KEYS", "ws-key")
        ws = MagicMock()
        ws.query_params = {}
        assert await verify_ws_api_key(ws) is False
