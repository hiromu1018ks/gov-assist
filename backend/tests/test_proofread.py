"""Tests for POST /api/proofread endpoint (§4.4, §5.2, §5.5)."""
import pytest
from unittest.mock import patch

from services.ai_client import ModelConfig

VALID_REQUEST = {
    "request_id": "test-req-001",
    "text": "これはテスト文書です。誤字があります。",
    "document_type": "official",
    "options": {
        "typo": True,
        "keigo": True,
        "terminology": True,
        "style": True,
        "legal": False,
        "readability": True,
    },
    "model": "kimi-k2.5",
}

AUTH_HEADERS = {"Authorization": "Bearer test-secret-token"}

MOCK_MODEL_CONFIG = ModelConfig(
    display_name="Kimi K2.5",
    max_tokens=4096,
    temperature=0.3,
    max_input_chars=8000,
    json_forced=True,
)


@pytest.fixture
def client(app_client):
    return app_client


class TestAuthAndValidation:
    def test_requires_auth(self, client):
        resp = client.post("/api/proofread", json=VALID_REQUEST)
        assert resp.status_code == 401

    def test_rejects_wrong_token(self, client):
        resp = client.post(
            "/api/proofread",
            json=VALID_REQUEST,
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert resp.status_code == 401

    @patch("routers.proofread.get_model_config")
    def test_unknown_model_returns_400(self, mock_config, client):
        mock_config.side_effect = KeyError("unknown-model")
        resp = client.post(
            "/api/proofread",
            json={**VALID_REQUEST, "model": "nonexistent-model"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data["error"] == "validation_error"
        assert "nonexistent-model" in data["message"]
        assert data["request_id"] == "test-req-001"

    @patch("routers.proofread.get_model_config")
    def test_valid_model_passes_validation(self, mock_config, client):
        mock_config.return_value = MOCK_MODEL_CONFIG
        resp = client.post("/api/proofread", json=VALID_REQUEST, headers=AUTH_HEADERS)
        # Currently returns 200 with stub response; will be refined in Task 2
        assert resp.status_code == 200

    def test_empty_text_returns_422(self, client):
        resp = client.post(
            "/api/proofread",
            json={**VALID_REQUEST, "text": ""},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 422

    def test_text_over_8000_chars_returns_422(self, client):
        resp = client.post(
            "/api/proofread",
            json={**VALID_REQUEST, "text": "あ" * 8001},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 422
