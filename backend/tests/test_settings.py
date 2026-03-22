"""Tests for GET/PUT /api/settings endpoint (§3.4, §5.1)."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-secret-token"}


@pytest.fixture
def client(app_client):
    return app_client


class TestGetSettings:
    def test_returns_200_with_auth(self, client, auth_headers):
        resp = client.get("/api/settings", headers=auth_headers)
        assert resp.status_code == 200

    def test_returns_history_limit(self, client, auth_headers):
        resp = client.get("/api/settings", headers=auth_headers)
        data = resp.json()
        assert "history_limit" in data
        assert isinstance(data["history_limit"], int)

    def test_default_history_limit_is_50(self, client, auth_headers):
        """DB に設定がない場合、デフォルト値 50 を返す"""
        resp = client.get("/api/settings", headers=auth_headers)
        assert resp.json()["history_limit"] == 50

    def test_returns_401_without_auth(self, client):
        resp = client.get("/api/settings")
        assert resp.status_code == 401


class TestPutSettings:
    def test_update_history_limit(self, client, auth_headers):
        resp = client.put(
            "/api/settings",
            json={"history_limit": 100},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["history_limit"] == 100

    def test_update_is_persisted(self, client, auth_headers):
        """更新後の GET で新しい値が返る"""
        client.put(
            "/api/settings",
            json={"history_limit": 75},
            headers=auth_headers,
        )
        resp = client.get("/api/settings", headers=auth_headers)
        assert resp.json()["history_limit"] == 75

    def test_update_to_minimum(self, client, auth_headers):
        resp = client.put(
            "/api/settings",
            json={"history_limit": 1},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["history_limit"] == 1

    def test_update_to_maximum(self, client, auth_headers):
        resp = client.put(
            "/api/settings",
            json={"history_limit": 200},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["history_limit"] == 200

    def test_update_below_minimum_returns_422(self, client, auth_headers):
        resp = client.put(
            "/api/settings",
            json={"history_limit": 0},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_update_above_maximum_returns_422(self, client, auth_headers):
        resp = client.put(
            "/api/settings",
            json={"history_limit": 201},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_update_missing_field_returns_422(self, client, auth_headers):
        resp = client.put(
            "/api/settings",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_update_without_auth_returns_401(self, client):
        resp = client.put(
            "/api/settings",
            json={"history_limit": 100},
        )
        assert resp.status_code == 401

    def test_update_with_wrong_token_returns_401(self, client):
        resp = client.put(
            "/api/settings",
            json={"history_limit": 100},
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert resp.status_code == 401

    def test_invalid_field_returns_422(self, client, auth_headers):
        resp = client.put(
            "/api/settings",
            json={"history_limit": "not-a-number"},
            headers=auth_headers,
        )
        assert resp.status_code == 422
