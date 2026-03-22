"""Tests for POST /api/proofread endpoint (§4.4, §5.2, §5.5)."""
import pytest
from unittest.mock import AsyncMock, patch

from schemas import (
    CorrectionItem,
    DiffBlock,
    DiffType,
    ProofreadStatus,
    StatusReason,
)
from services.ai_client import AIClientError, ModelConfig
from services.diff_service import DiffResult
from services.response_parser import ParseResult

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
    "model": "gpt-oss-120b",
}

AUTH_HEADERS = {"Authorization": "Bearer test-secret-token"}

MOCK_MODEL_CONFIG = ModelConfig(
    display_name="GPT-OSS 120B",
    max_tokens=4096,
    temperature=0.3,
    max_input_chars=8000,
    json_forced=True,
)


@pytest.fixture
def client(app_client):
    return app_client


class TestAuthAndValidation:
    @pytest.mark.skip(reason="Auth disabled for localhost MVP")
    def test_requires_auth(self, client):
        resp = client.post("/api/proofread", json=VALID_REQUEST)
        assert resp.status_code == 401

    @pytest.mark.skip(reason="Auth disabled for localhost MVP")
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

    @patch("routers.proofread.compute_diffs")
    @patch("routers.proofread.parse_ai_response", new_callable=AsyncMock)
    @patch("routers.proofread.create_ai_client")
    @patch("routers.proofread.build_prompts")
    @patch("routers.proofread.get_model_config")
    def test_valid_model_passes_validation(self, mock_config, mock_build, mock_create, mock_parse, mock_diffs, client):
        mock_config.return_value = MOCK_MODEL_CONFIG
        mock_build.return_value = ("system_prompt", "user_prompt")
        mock_ai = AsyncMock()
        mock_ai.complete.return_value = '{"corrected_text": "テスト", "summary": "OK", "corrections": []}'
        mock_create.return_value = mock_ai
        mock_parse.return_value = ParseResult(
            corrected_text="テスト", summary="OK",
            corrections=[], status=ProofreadStatus.SUCCESS, status_reason=None,
        )
        mock_diffs.return_value = DiffResult(
            diffs=[], warnings=[],
            status=ProofreadStatus.SUCCESS, status_reason=None, corrections=[],
        )
        resp = client.post("/api/proofread", json=VALID_REQUEST, headers=AUTH_HEADERS)
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


class TestSuccessPath:
    @patch("routers.proofread.compute_diffs")
    @patch("routers.proofread.parse_ai_response", new_callable=AsyncMock)
    @patch("routers.proofread.create_ai_client")
    @patch("routers.proofread.build_prompts")
    @patch("routers.proofread.get_model_config")
    def test_successful_proofread(
        self, mock_config, mock_build, mock_create, mock_parse, mock_diffs, client,
    ):
        mock_config.return_value = MOCK_MODEL_CONFIG
        mock_build.return_value = ("system_prompt", "user_prompt")
        mock_ai = AsyncMock()
        mock_ai.complete.return_value = '{"corrected_text": "...", "summary": "...", "corrections": []}'
        mock_create.return_value = mock_ai
        mock_parse.return_value = ParseResult(
            corrected_text="これはテスト文書です。誤字がありません。",
            summary="1件の修正を行いました。",
            corrections=[
                CorrectionItem(
                    original="あります", corrected="ありません",
                    reason="否定の誤り", category="誤字脱字",
                ),
            ],
            status=ProofreadStatus.SUCCESS,
            status_reason=None,
        )
        mock_diffs.return_value = DiffResult(
            diffs=[
                DiffBlock(type=DiffType.EQUAL, text="これはテスト文書です。誤字が", start=0),
                DiffBlock(type=DiffType.DELETE, text="あり", start=14, reason="否定の誤り"),
                DiffBlock(type=DiffType.INSERT, text="ありません", start=14, position="after", reason="否定の誤り"),
                DiffBlock(type=DiffType.EQUAL, text="。", start=16),
            ],
            warnings=[],
            status=ProofreadStatus.SUCCESS,
            status_reason=None,
            corrections=[
                CorrectionItem(
                    original="あります", corrected="ありません",
                    reason="否定の誤り", category="誤字脱字", diff_matched=True,
                ),
            ],
        )

        resp = client.post("/api/proofread", json=VALID_REQUEST, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["request_id"] == "test-req-001"
        assert data["status"] == "success"
        assert data["status_reason"] is None
        assert data["corrected_text"] == "これはテスト文書です。誤字がありません。"
        assert data["summary"] == "1件の修正を行いました。"
        assert len(data["diffs"]) == 4
        assert data["diffs"][1]["type"] == "delete"
        assert data["diffs"][2]["position"] == "after"
        assert len(data["corrections"]) == 1
        assert data["corrections"][0]["diff_matched"] is True
        assert data["warnings"] == []

    @patch("routers.proofread.compute_diffs")
    @patch("routers.proofread.parse_ai_response", new_callable=AsyncMock)
    @patch("routers.proofread.create_ai_client")
    @patch("routers.proofread.build_prompts")
    @patch("routers.proofread.get_model_config")
    def test_large_rewrite_appends_warning_to_summary(
        self, mock_config, mock_build, mock_create, mock_parse, mock_diffs, client,
    ):
        mock_config.return_value = MOCK_MODEL_CONFIG
        mock_build.return_value = ("s", "u")
        mock_create.return_value = AsyncMock()
        mock_parse.return_value = ParseResult(
            corrected_text="大幅修正テキスト", summary="5件の修正を行いました。",
            corrections=[], status=ProofreadStatus.SUCCESS, status_reason=None,
        )
        mock_diffs.return_value = DiffResult(
            diffs=[], warnings=["large_rewrite"],
            status=ProofreadStatus.SUCCESS, status_reason=None, corrections=[],
        )

        resp = client.post("/api/proofread", json=VALID_REQUEST, headers=AUTH_HEADERS)
        data = resp.json()
        assert data["warnings"] == ["large_rewrite"]
        assert "広範囲を書き換えました" in data["summary"]
        assert "5件の修正を行いました。" in data["summary"]

    @patch("routers.proofread.compute_diffs")
    @patch("routers.proofread.parse_ai_response", new_callable=AsyncMock)
    @patch("routers.proofread.create_ai_client")
    @patch("routers.proofread.build_prompts")
    @patch("routers.proofread.get_model_config")
    def test_large_rewrite_with_null_summary(
        self, mock_config, mock_build, mock_create, mock_parse, mock_diffs, client,
    ):
        mock_config.return_value = MOCK_MODEL_CONFIG
        mock_build.return_value = ("s", "u")
        mock_create.return_value = AsyncMock()
        mock_parse.return_value = ParseResult(
            corrected_text="text", summary=None,
            corrections=[], status=ProofreadStatus.SUCCESS, status_reason=None,
        )
        mock_diffs.return_value = DiffResult(
            diffs=[], warnings=["large_rewrite"],
            status=ProofreadStatus.SUCCESS, status_reason=None, corrections=[],
        )

        resp = client.post("/api/proofread", json=VALID_REQUEST, headers=AUTH_HEADERS)
        data = resp.json()
        from routers.proofread import LARGE_REWRITE_SUMMARY
        assert data["summary"] == LARGE_REWRITE_SUMMARY


class TestAIErrorHandling:
    @patch("routers.proofread.create_ai_client")
    @patch("routers.proofread.build_prompts")
    @patch("routers.proofread.get_model_config")
    def test_ai_timeout_returns_504(self, mock_config, mock_build, mock_create, client):
        mock_config.return_value = MOCK_MODEL_CONFIG
        mock_build.return_value = ("s", "u")
        mock_ai = AsyncMock()
        mock_ai.complete.side_effect = AIClientError("ai_timeout", "タイムアウト")
        mock_create.return_value = mock_ai

        resp = client.post("/api/proofread", json=VALID_REQUEST, headers=AUTH_HEADERS)
        assert resp.status_code == 504
        data = resp.json()
        assert data["error"] == "ai_timeout"
        assert data["request_id"] == "test-req-001"
        assert "タイムアウト" in data["message"]

    @patch("routers.proofread.create_ai_client")
    @patch("routers.proofread.build_prompts")
    @patch("routers.proofread.get_model_config")
    def test_ai_rate_limit_returns_502(self, mock_config, mock_build, mock_create, client):
        mock_config.return_value = MOCK_MODEL_CONFIG
        mock_build.return_value = ("s", "u")
        mock_ai = AsyncMock()
        mock_ai.complete.side_effect = AIClientError("ai_rate_limit", "レート制限")
        mock_create.return_value = mock_ai

        resp = client.post("/api/proofread", json=VALID_REQUEST, headers=AUTH_HEADERS)
        assert resp.status_code == 502
        assert resp.json()["error"] == "ai_rate_limit"

    @patch("routers.proofread.create_ai_client")
    @patch("routers.proofread.build_prompts")
    @patch("routers.proofread.get_model_config")
    def test_ai_invalid_response_returns_502(self, mock_config, mock_build, mock_create, client):
        mock_config.return_value = MOCK_MODEL_CONFIG
        mock_build.return_value = ("s", "u")
        mock_ai = AsyncMock()
        mock_ai.complete.side_effect = AIClientError("ai_invalid_response", "APIエラー")
        mock_create.return_value = mock_ai

        resp = client.post("/api/proofread", json=VALID_REQUEST, headers=AUTH_HEADERS)
        assert resp.status_code == 502
        assert resp.json()["error"] == "ai_invalid_response"

    @patch("routers.proofread.create_ai_client")
    @patch("routers.proofread.build_prompts")
    @patch("routers.proofread.get_model_config")
    def test_unknown_ai_error_code_returns_502(self, mock_config, mock_build, mock_create, client):
        """未知の AI エラーコードはデフォルトで 502 を返す"""
        mock_config.return_value = MOCK_MODEL_CONFIG
        mock_build.return_value = ("s", "u")
        mock_ai = AsyncMock()
        mock_ai.complete.side_effect = AIClientError("unknown_code", "不明なエラー")
        mock_create.return_value = mock_ai

        resp = client.post("/api/proofread", json=VALID_REQUEST, headers=AUTH_HEADERS)
        assert resp.status_code == 502
        data = resp.json()
        # Unknown error codes are sanitized to "ai_invalid_response"
        assert data["error"] == "ai_invalid_response"


class TestParseAndDiffErrors:
    @patch("routers.proofread.parse_ai_response", new_callable=AsyncMock)
    @patch("routers.proofread.create_ai_client")
    @patch("routers.proofread.build_prompts")
    @patch("routers.proofread.get_model_config")
    def test_parse_error_returns_502(
        self, mock_config, mock_build, mock_create, mock_parse, client,
    ):
        mock_config.return_value = MOCK_MODEL_CONFIG
        mock_build.return_value = ("s", "u")
        mock_create.return_value = AsyncMock()
        mock_parse.return_value = ParseResult(
            corrected_text="", summary=None, corrections=[],
            status=ProofreadStatus.ERROR, status_reason=StatusReason.PARSE_FALLBACK,
        )

        resp = client.post("/api/proofread", json=VALID_REQUEST, headers=AUTH_HEADERS)
        assert resp.status_code == 502
        data = resp.json()
        assert data["error"] == "ai_parse_error"
        assert data["request_id"] == "test-req-001"

    @patch("routers.proofread.parse_ai_response", new_callable=AsyncMock)
    @patch("routers.proofread.create_ai_client")
    @patch("routers.proofread.build_prompts")
    @patch("routers.proofread.get_model_config")
    def test_parse_partial_returns_200_with_partial_status(
        self, mock_config, mock_build, mock_create, mock_parse, client,
    ):
        mock_config.return_value = MOCK_MODEL_CONFIG
        mock_build.return_value = ("s", "u")
        mock_create.return_value = AsyncMock()
        mock_parse.return_value = ParseResult(
            corrected_text="フォールバック抽出テキスト",
            summary=None, corrections=[],
            status=ProofreadStatus.PARTIAL, status_reason=StatusReason.PARSE_FALLBACK,
        )

        resp = client.post("/api/proofread", json=VALID_REQUEST, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "partial"
        assert data["status_reason"] == "parse_fallback"
        assert data["corrected_text"] == "フォールバック抽出テキスト"
        assert data["diffs"] == []
        assert data["warnings"] == []

    @patch("routers.proofread.compute_diffs")
    @patch("routers.proofread.parse_ai_response", new_callable=AsyncMock)
    @patch("routers.proofread.create_ai_client")
    @patch("routers.proofread.build_prompts")
    @patch("routers.proofread.get_model_config")
    def test_diff_timeout_returns_200_with_partial_status(
        self, mock_config, mock_build, mock_create, mock_parse, mock_diffs, client,
    ):
        mock_config.return_value = MOCK_MODEL_CONFIG
        mock_build.return_value = ("s", "u")
        mock_create.return_value = AsyncMock()
        mock_parse.return_value = ParseResult(
            corrected_text="校正済みテキスト", summary="2件の修正",
            corrections=[], status=ProofreadStatus.SUCCESS, status_reason=None,
        )
        mock_diffs.return_value = DiffResult(
            diffs=[], warnings=[],
            status=ProofreadStatus.PARTIAL, status_reason=StatusReason.DIFF_TIMEOUT,
            corrections=[],
        )

        resp = client.post("/api/proofread", json=VALID_REQUEST, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "partial"
        assert data["status_reason"] == "diff_timeout"
        assert data["corrected_text"] == "校正済みテキスト"
        assert data["summary"] == "2件の修正"

    @patch("routers.proofread.build_prompts")
    @patch("routers.proofread.get_model_config")
    def test_internal_error_returns_500(self, mock_config, mock_build, client):
        mock_config.return_value = MOCK_MODEL_CONFIG
        mock_build.side_effect = RuntimeError("unexpected crash")

        resp = client.post("/api/proofread", json=VALID_REQUEST, headers=AUTH_HEADERS)
        assert resp.status_code == 500
        data = resp.json()
        assert data["error"] == "internal_error"
        assert data["request_id"] == "test-req-001"
        assert "内部エラー" in data["message"]
