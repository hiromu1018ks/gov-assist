# test_export_integration.py
"""Integration tests for POST /api/export/docx — edge cases."""
import pytest

AUTH_HEADERS = {"Authorization": "Bearer test-secret-token"}


@pytest.fixture
def client(app_client):
    return app_client


class TestExportEdgeCases:
    """Edge cases for docx export."""

    def test_japanese_text_export(self, client):
        """日本語テキストが正しくエクスポートされる"""
        resp = client.post(
            "/api/export/docx",
            json={"corrected_text": "申請書を提出してください。", "document_type": "official"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert len(resp.content) > 0

    def test_multiline_with_bullets_export(self, client):
        """箇条書きを含むテキストのエクスポート"""
        text = "報告書\n\n・第1章 概要\n概要を記載します。\n\n・第2章 詳細\n詳細を記載します。"
        resp = client.post(
            "/api/export/docx",
            json={"corrected_text": text, "document_type": "report"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        assert len(resp.content) > 0

    def test_single_character_text(self, client):
        """最小文字数（1文字）のテキスト"""
        resp = client.post(
            "/api/export/docx",
            json={"corrected_text": "あ", "document_type": "other"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200

    def test_all_document_types(self, client):
        """全文書種別でエクスポート可能"""
        for doc_type in ["email", "report", "official", "other"]:
            resp = client.post(
                "/api/export/docx",
                json={"corrected_text": f"{doc_type}テスト", "document_type": doc_type},
                headers=AUTH_HEADERS,
            )
            assert resp.status_code == 200, f"Failed for document_type={doc_type}"

    @pytest.mark.skip(reason="Auth disabled for localhost MVP")
    def test_requires_auth(self, client):
        resp = client.post(
            "/api/export/docx",
            json={"corrected_text": "テスト", "document_type": "official"},
        )
        assert resp.status_code == 401
