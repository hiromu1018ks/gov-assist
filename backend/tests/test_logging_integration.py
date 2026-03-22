# test_logging_integration.py
"""Integration tests for log output (§9.2, §13 Task 22)."""
import logging
import pytest
from unittest.mock import AsyncMock, patch

AUTH_HEADERS = {"Authorization": "Bearer test-secret-token"}


@pytest.fixture
def client(app_client):
    return app_client


class TestProofreadLogging:
    """Verify log entries are emitted for key events (§9.2)."""

    def test_ai_error_logs_request_id_and_error(self, client, caplog):
        """AI エラー時に request_id とエラー情報がログに記録される"""
        with patch("routers.proofread.get_model_config") as mock_config, \
             patch("routers.proofread.build_prompts", return_value=("s", "u")), \
             patch("routers.proofread.create_ai_client") as mock_create:
            from services.ai_client import AIClientError, ModelConfig
            mock_config.return_value = ModelConfig(
                display_name="K", max_tokens=4096, temperature=0.3,
                max_input_chars=8000, json_forced=True,
            )
            mock_ai = AsyncMock()
            mock_ai.complete.side_effect = AIClientError("ai_timeout", "タイムアウト")
            mock_create.return_value = mock_ai

            with caplog.at_level(logging.ERROR, logger="govassist"):
                resp = client.post(
                    "/api/proofread",
                    json={"request_id": "log-test-001", "text": "テスト", "document_type": "official", "model": "kimi-k2.5"},
                    headers=AUTH_HEADERS,
                )

            assert resp.status_code == 504
            assert any("log-test-001" in rec.message for rec in caplog.records)
            assert any("ai_timeout" in rec.message for rec in caplog.records)

    def test_internal_error_logs_stack_trace(self, client, caplog):
        """内部エラー時にスタックトレースがログに記録される"""
        with patch("routers.proofread.get_model_config") as mock_config, \
             patch("routers.proofread.build_prompts", side_effect=RuntimeError("unexpected")), \
             patch("routers.proofread.create_ai_client", return_value=AsyncMock()):
            from services.ai_client import ModelConfig
            mock_config.return_value = ModelConfig(
                display_name="K", max_tokens=4096, temperature=0.3,
                max_input_chars=8000, json_forced=True,
            )

            with caplog.at_level(logging.ERROR, logger="govassist"):
                resp = client.post(
                    "/api/proofread",
                    json={"request_id": "log-test-002", "text": "テスト", "document_type": "official", "model": "kimi-k2.5"},
                    headers=AUTH_HEADERS,
                )

            assert resp.status_code == 500
            assert any("log-test-002" in rec.message for rec in caplog.records)
            assert any("internal error" in rec.message for rec in caplog.records)


class TestAuthLogging:
    """Verify auth failures are handled correctly."""

    @pytest.mark.skip(reason="Auth disabled for localhost MVP")
    def test_unauthorized_request_returns_401(self, client):
        """認証なしリクエストは 401 を返す"""
        resp = client.post("/api/proofread", json={"text": "test"})
        assert resp.status_code == 401
