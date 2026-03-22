"""Integration tests for GET /api/history — search + pagination and edge cases."""
import pytest
from datetime import datetime, timedelta

AUTH_HEADERS = {"Authorization": "Bearer test-secret-token"}


@pytest.fixture
def client(app_client):
    return app_client


def _create_history(client, input_text, doc_type="official", memo=None):
    """Helper to create a history record via the API."""
    result = {
        "request_id": "test-req",
        "status": "success",
        "status_reason": None,
        "warnings": [],
        "corrected_text": input_text + "（校正済み）",
        "summary": "OK",
        "corrections": [],
        "diffs": [],
    }
    body = {
        "input_text": input_text,
        "result": result,
        "model": "kimi-k2.5",
        "document_type": doc_type,
    }
    if memo is not None:
        body["memo"] = memo
    resp = client.post("/api/history", json=body, headers=AUTH_HEADERS)
    return resp


class TestSearchPagination:
    """Search query combined with pagination."""

    def test_search_with_limit_and_offset(self, client):
        """検索キーワード + ページネーションの組み合わせ"""
        for i in range(5):
            _create_history(client, f"申請書サンプル{i:02d}")

        resp = client.get("/api/history?q=申請書&limit=2&offset=0", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 5
        assert len(data["items"]) <= 2

    def test_search_returns_empty_for_no_match(self, client):
        _create_history(client, "申請書のテスト")
        resp = client.get("/api/history?q=存在しないキーワード", headers=AUTH_HEADERS)
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_search_with_document_type_filter(self, client):
        _create_history(client, "メールのテスト", doc_type="email")
        _create_history(client, "報告書のテスト", doc_type="report")

        resp = client.get("/api/history?document_type=email", headers=AUTH_HEADERS)
        data = resp.json()
        assert data["total"] >= 1
        assert all(item["document_type"] == "email" for item in data["items"])

    def test_offset_beyond_total_returns_empty(self, client):
        _create_history(client, "テスト")
        resp = client.get("/api/history?offset=999", headers=AUTH_HEADERS)
        data = resp.json()
        assert data["items"] == []
        assert data["total"] >= 1


class TestHistoryEdgeCases:
    """Edge cases for history CRUD."""

    def test_empty_query_returns_all(self, client):
        _create_history(client, "テスト1")
        _create_history(client, "テスト2")
        resp = client.get("/api/history?q=", headers=AUTH_HEADERS)
        data = resp.json()
        assert data["total"] >= 2

    def test_null_query_returns_all(self, client):
        _create_history(client, "テスト1")
        resp = client.get("/api/history", headers=AUTH_HEADERS)
        data = resp.json()
        assert data["total"] >= 1

    def test_delete_nonexistent_returns_404(self, client):
        resp = client.delete("/api/history/99999", headers=AUTH_HEADERS)
        assert resp.status_code == 404

    def test_get_nonexistent_returns_404(self, client):
        resp = client.get("/api/history/99999", headers=AUTH_HEADERS)
        assert resp.status_code == 404

    def test_patch_nonexistent_returns_404(self, client):
        resp = client.patch("/api/history/99999", json={"memo": "test"}, headers=AUTH_HEADERS)
        assert resp.status_code == 404

    def test_special_characters_in_search_query(self, client):
        """LIKE パターン文字が含まれてもエラーにならない"""
        _create_history(client, "テストデータ")
        resp = client.get("/api/history?q=%25_%30", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    def test_items_returned_in_descending_order(self, client):
        _create_history(client, "最初のレコード")
        _create_history(client, "2番目のレコード")
        _create_history(client, "3番目のレコード")

        resp = client.get("/api/history", headers=AUTH_HEADERS)
        data = resp.json()
        assert data["total"] >= 3
        dates = [item["created_at"] for item in data["items"]]
        assert dates == sorted(dates, reverse=True)

    def test_date_range_filter(self, client):
        """日付範囲フィルタのテスト"""
        _create_history(client, "テストデータ")

        yesterday = (datetime.now() - timedelta(days=1)).isoformat() + "Z"
        tomorrow = (datetime.now() + timedelta(days=1)).isoformat() + "Z"

        resp = client.get(f"/api/history?date_from={yesterday}&date_to={tomorrow}", headers=AUTH_HEADERS)
        data = resp.json()
        assert data["total"] >= 1
