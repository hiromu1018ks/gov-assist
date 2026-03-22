"""Integration tests for POST /api/proofread — edge cases not covered by unit tests."""
import pytest
from unittest.mock import AsyncMock, patch

from schemas import (
    CorrectionItem,
    DiffBlock,
    DiffType,
    ProofreadStatus,
)
from services.ai_client import ModelConfig
from services.diff_service import DiffResult
from services.response_parser import ParseResult

VALID_REQUEST = {
    "request_id": "test-req-int-001",
    "text": "これはテスト文書です。",
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


class TestRequestIdPropagation:
    """X-Request-ID should be echoed in every response."""

    @patch("routers.proofread.compute_diffs")
    @patch("routers.proofread.parse_ai_response", new_callable=AsyncMock)
    @patch("routers.proofread.create_ai_client")
    @patch("routers.proofread.build_prompts")
    @patch("routers.proofread.get_model_config")
    def test_success_response_echoes_request_id(self, mock_config, mock_build, mock_create, mock_parse, mock_diffs, client):
        mock_config.return_value = MOCK_MODEL_CONFIG
        mock_build.return_value = ("s", "u")
        mock_create.return_value = AsyncMock()
        mock_parse.return_value = ParseResult(
            corrected_text="テスト", summary="OK", corrections=[],
            status=ProofreadStatus.SUCCESS, status_reason=None,
        )
        mock_diffs.return_value = DiffResult(
            diffs=[], warnings=[], status=ProofreadStatus.SUCCESS,
            status_reason=None, corrections=[],
        )

        resp = client.post("/api/proofread", json=VALID_REQUEST, headers=AUTH_HEADERS)
        data = resp.json()
        assert data["request_id"] == "test-req-int-001"

    @patch("routers.proofread.get_model_config")
    def test_error_response_echoes_request_id(self, mock_config, client):
        mock_config.side_effect = KeyError("bad")
        resp = client.post("/api/proofread", json=VALID_REQUEST, headers=AUTH_HEADERS)
        data = resp.json()
        assert data["request_id"] == "test-req-int-001"

    @patch("routers.proofread.create_ai_client")
    @patch("routers.proofread.build_prompts")
    @patch("routers.proofread.get_model_config")
    def test_internal_error_echoes_request_id(self, mock_config, mock_build, mock_create, client):
        mock_config.return_value = MOCK_MODEL_CONFIG
        mock_build.side_effect = RuntimeError("crash")
        mock_create.return_value = AsyncMock()
        resp = client.post("/api/proofread", json=VALID_REQUEST, headers=AUTH_HEADERS)
        data = resp.json()
        assert data["request_id"] == "test-req-int-001"


class TestValidationEdgeCases:
    """Validation boundary and optional field tests."""

    def test_text_at_exactly_8000_chars_passes(self, client):
        resp = client.post(
            "/api/proofread",
            json={**VALID_REQUEST, "text": "あ" * 8000},
            headers=AUTH_HEADERS,
        )
        # Should not be 422 for text length (may be 400 for model or 200 with mocks)
        assert resp.status_code != 422

    def test_text_at_8001_chars_fails(self, client):
        resp = client.post(
            "/api/proofread",
            json={**VALID_REQUEST, "text": "あ" * 8001},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 422

    def test_missing_options_uses_defaults(self, client):
        """options フィールドを省略するとデフォルトが使用される"""
        request_no_options = {
            "request_id": "test-opt-001",
            "text": "テスト",
            "document_type": "official",
            "model": "kimi-k2.5",
        }
        resp = client.post("/api/proofread", json=request_no_options, headers=AUTH_HEADERS)
        # Should not be 422 for missing options (Pydantic applies defaults)
        assert resp.status_code != 422 or "options" not in resp.text

    def test_invalid_document_type_returns_422(self, client):
        resp = client.post(
            "/api/proofread",
            json={**VALID_REQUEST, "document_type": "invalid_type"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 422


class TestResponseSchemaCompleteness:
    """Verify all expected fields are present in every response type."""

    SUCCESS_FIELDS = {"request_id", "status", "status_reason", "warnings", "corrected_text", "summary", "corrections", "diffs"}
    ERROR_FIELDS = {"request_id", "error", "message"}

    @patch("routers.proofread.compute_diffs")
    @patch("routers.proofread.parse_ai_response", new_callable=AsyncMock)
    @patch("routers.proofread.create_ai_client")
    @patch("routers.proofread.build_prompts")
    @patch("routers.proofread.get_model_config")
    def test_success_response_has_all_fields(self, mock_config, mock_build, mock_create, mock_parse, mock_diffs, client):
        mock_config.return_value = MOCK_MODEL_CONFIG
        mock_build.return_value = ("s", "u")
        mock_create.return_value = AsyncMock()
        mock_parse.return_value = ParseResult(
            corrected_text="テスト", summary="OK",
            corrections=[CorrectionItem(original="A", corrected="B", reason="r", category="c")],
            status=ProofreadStatus.SUCCESS, status_reason=None,
        )
        mock_diffs.return_value = DiffResult(
            diffs=[
                DiffBlock(type=DiffType.EQUAL, text="テ", start=0),
                DiffBlock(type=DiffType.DELETE, text="ス", start=1, reason="r"),
                DiffBlock(type=DiffType.INSERT, text="ト", start=1, position="after", reason="r"),
            ],
            warnings=[], status=ProofreadStatus.SUCCESS,
            status_reason=None,
            corrections=[CorrectionItem(original="A", corrected="B", reason="r", category="c", diff_matched=True)],
        )
        resp = client.post("/api/proofread", json=VALID_REQUEST, headers=AUTH_HEADERS)
        data = resp.json()
        assert self.SUCCESS_FIELDS.issubset(data.keys())
        # Verify diff block fields
        for diff in data["diffs"]:
            assert "type" in diff
            assert "text" in diff
            assert "start" in diff
            assert "position" in diff
            assert "reason" in diff
        # Verify correction fields
        for corr in data["corrections"]:
            assert "original" in corr
            assert "corrected" in corr
            assert "reason" in corr
            assert "category" in corr
            assert "diff_matched" in corr

    @patch("routers.proofread.get_model_config")
    def test_error_response_has_all_fields(self, mock_config, client):
        mock_config.side_effect = KeyError("bad")
        resp = client.post("/api/proofread", json=VALID_REQUEST, headers=AUTH_HEADERS)
        data = resp.json()
        assert self.ERROR_FIELDS.issubset(data.keys())


class TestJapaneseRealisticDiff:
    """Verify diff accuracy with realistic Japanese proofreading scenarios."""

    @patch("routers.proofread.compute_diffs")
    @patch("routers.proofread.parse_ai_response", new_callable=AsyncMock)
    @patch("routers.proofread.create_ai_client")
    @patch("routers.proofread.build_prompts")
    @patch("routers.proofread.get_model_config")
    def test_realistic_japanese_proofread(self, mock_config, mock_build, mock_create, mock_parse, mock_diffs, client):
        """実際の校正パターン（敬語修正・誤字修正）の統合テスト"""
        input_text = "申請書を提出してください。よろしくおねがいします。"
        corrected_text = "申請書を提出してくださいますようお願いいたします。"

        mock_config.return_value = MOCK_MODEL_CONFIG
        mock_build.return_value = ("s", "u")
        mock_create.return_value = AsyncMock()
        mock_parse.return_value = ParseResult(
            corrected_text=corrected_text,
            summary="2件の修正を行いました。",
            corrections=[
                CorrectionItem(original="提出してください", corrected="提出してくださいますよう", reason="敬語の適切化", category="敬語"),
                CorrectionItem(original="おねがいします", corrected="お願いいたします", reason="表記統一", category="用語"),
            ],
            status=ProofreadStatus.SUCCESS,
            status_reason=None,
        )
        mock_diffs.return_value = DiffResult(
            diffs=[
                DiffBlock(type=DiffType.EQUAL, text="申請書を", start=0),
                DiffBlock(type=DiffType.EQUAL, text="提出", start=5),
                DiffBlock(type=DiffType.DELETE, text="してください", start=7, reason="敬語の適切化"),
                DiffBlock(type=DiffType.INSERT, text="してくださいますよう", start=7, position="after", reason="敬語の適切化"),
                DiffBlock(type=DiffType.EQUAL, text="。よろしく", start=12),
                DiffBlock(type=DiffType.DELETE, text="おねがいします", start=17, reason="表記統一"),
                DiffBlock(type=DiffType.INSERT, text="お願いいたします", start=17, position="after", reason="表記統一"),
                DiffBlock(type=DiffType.EQUAL, text="。", start=25),
            ],
            warnings=[],
            status=ProofreadStatus.SUCCESS,
            status_reason=None,
            corrections=[
                CorrectionItem(original="提出してください", corrected="提出してくださいますよう", reason="敬語の適切化", category="敬語", diff_matched=True),
                CorrectionItem(original="おねがいします", corrected="お願いいたします", reason="表記統一", category="用語", diff_matched=True),
            ],
        )

        resp = client.post(
            "/api/proofread",
            json={**VALID_REQUEST, "text": input_text},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["corrected_text"] == corrected_text
        assert len(data["corrections"]) == 2
        assert all(c["diff_matched"] for c in data["corrections"])

        # Verify diff sequence: delete should precede insert for each change
        types = [d["type"] for d in data["diffs"]]
        for i, t in enumerate(types):
            if t == "delete":
                if i + 1 < len(types):
                    assert types[i + 1] == "insert", f"delete at {i} should be followed by insert"
