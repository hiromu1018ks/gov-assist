"""Tests for GET /api/models endpoint (§4.2, §5.1)."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(app_client):
    return app_client


class TestGetModels:
    def test_returns_200_with_auth(self, client):
        resp = client.get(
            "/api/models",
            headers={"Authorization": "Bearer test-secret-token"},
        )
        assert resp.status_code == 200

    def test_returns_models_list(self, client):
        resp = client.get(
            "/api/models",
            headers={"Authorization": "Bearer test-secret-token"},
        )
        data = resp.json()
        assert "models" in data
        assert isinstance(data["models"], list)
        assert len(data["models"]) >= 1

    def test_kimi_k25_in_response(self, client):
        resp = client.get(
            "/api/models",
            headers={"Authorization": "Bearer test-secret-token"},
        )
        models = resp.json()["models"]
        kimi = next(m for m in models if m["model_id"] == "gpt-oss-120b")
        assert kimi["display_name"] == "GPT-OSS 120B"
        assert kimi["max_tokens"] == 4096
        assert kimi["temperature"] == 0.3
        assert kimi["max_input_chars"] == 8000
        assert kimi["json_forced"] is True

    def test_model_fields_are_complete(self, client):
        resp = client.get(
            "/api/models",
            headers={"Authorization": "Bearer test-secret-token"},
        )
        model = resp.json()["models"][0]
        expected_keys = {"model_id", "display_name", "max_tokens", "temperature", "max_input_chars", "json_forced"}
        assert set(model.keys()) == expected_keys

    @pytest.mark.skip(reason="Auth disabled for localhost MVP")
    def test_returns_401_without_auth(self, client):
        resp = client.get("/api/models")
        assert resp.status_code == 401

    @pytest.mark.skip(reason="Auth disabled for localhost MVP")
    def test_returns_401_with_wrong_token(self, client):
        resp = client.get(
            "/api/models",
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert resp.status_code == 401
