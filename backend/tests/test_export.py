"""Tests for POST /api/export/docx endpoint (§5.3, §6.2)."""
import pytest
from unittest.mock import patch

AUTH_HEADERS = {"Authorization": "Bearer test-secret-token"}

VALID_REQUEST = {
    "corrected_text": "校正済みテキストです。",
    "document_type": "official",
}


@pytest.fixture
def client(app_client):
    return app_client


class TestAuthAndValidation:
    @pytest.mark.skip(reason="Auth disabled for localhost MVP")
    def test_requires_auth(self, client):
        resp = client.post("/api/export/docx", json=VALID_REQUEST)
        assert resp.status_code == 401

    @pytest.mark.skip(reason="Auth disabled for localhost MVP")
    def test_rejects_wrong_token(self, client):
        resp = client.post(
            "/api/export/docx",
            json=VALID_REQUEST,
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert resp.status_code == 401

    def test_empty_corrected_text_returns_422(self, client):
        resp = client.post(
            "/api/export/docx",
            json={"corrected_text": "", "document_type": "official"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 422

    def test_invalid_document_type_returns_422(self, client):
        resp = client.post(
            "/api/export/docx",
            json={"corrected_text": "テスト", "document_type": "invalid"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 422

    def test_missing_document_type_returns_422(self, client):
        resp = client.post(
            "/api/export/docx",
            json={"corrected_text": "テスト"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 422


class TestSuccessPath:
    def test_returns_docx_binary(self, client):
        resp = client.post("/api/export/docx", json=VALID_REQUEST, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.content[:2] == b"PK"  # ZIP/docx header

    def test_content_type_is_docx(self, client):
        resp = client.post("/api/export/docx", json=VALID_REQUEST, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in resp.headers["content-type"]

    def test_content_disposition_attachment(self, client):
        resp = client.post("/api/export/docx", json=VALID_REQUEST, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        cd = resp.headers.get("content-disposition", "")
        assert "attachment" in cd
        assert ".docx" in cd
        assert "filename*=UTF-8''" in cd

    def test_multiline_text(self, client):
        request = {
            "corrected_text": "第一段落\n\n第二段落\n\n・箇条書き項目",
            "document_type": "email",
        }
        resp = client.post("/api/export/docx", json=request, headers=AUTH_HEADERS)
        assert resp.status_code == 200

    def test_all_document_types(self, client):
        for doc_type in ["email", "report", "official", "other"]:
            request = {"corrected_text": "テスト", "document_type": doc_type}
            resp = client.post("/api/export/docx", json=request, headers=AUTH_HEADERS)
            assert resp.status_code == 200, f"Failed for document_type={doc_type}"


class TestErrorHandling:
    @patch("routers.export.generate_docx")
    def test_service_error_returns_500(self, mock_generate, client):
        mock_generate.side_effect = RuntimeError("docx generation failed")
        resp = client.post("/api/export/docx", json=VALID_REQUEST, headers=AUTH_HEADERS)
        assert resp.status_code == 500
        data = resp.json()
        assert data["error"] == "internal_error"
        assert "内部エラー" in data["message"]
