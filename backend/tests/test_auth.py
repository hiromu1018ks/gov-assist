# backend/tests/test_auth.py
"""Tests for Bearer token authentication dependency (§8.2)."""
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from main import verify_token, get_app_token


def _create_test_app() -> FastAPI:
    """Create a minimal app with a protected endpoint for testing auth."""
    test_app = FastAPI()

    @test_app.get("/api/protected")
    async def protected(token: str = Depends(verify_token)):
        return {"status": "ok", "token_preview": token[:4] + "..."}

    return test_app


@pytest.fixture
def client():
    app = _create_test_app()
    app.dependency_overrides[get_app_token] = lambda: "test-secret-token"
    return TestClient(app)


class TestValidToken:
    def test_correct_token_returns_200(self, client):
        response = client.get(
            "/api/protected",
            headers={"Authorization": "Bearer test-secret-token"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_token_value_returned(self, client):
        response = client.get(
            "/api/protected",
            headers={"Authorization": "Bearer test-secret-token"},
        )
        assert response.json()["token_preview"] == "test..."


class TestMissingAuthHeader:
    def test_no_authorization_header_returns_401(self, client):
        response = client.get("/api/protected")
        assert response.status_code == 401

    def test_empty_string_header_returns_401(self, client):
        response = client.get("/api/protected", headers={"Authorization": ""})
        assert response.status_code == 401


class TestInvalidToken:
    def test_wrong_token_returns_401(self, client):
        response = client.get(
            "/api/protected",
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert response.status_code == 401

    def test_empty_bearer_value_returns_401(self, client):
        response = client.get(
            "/api/protected",
            headers={"Authorization": "Bearer "},
        )
        assert response.status_code == 401

    def test_extra_whitespace_in_token_returns_401(self, client):
        response = client.get(
            "/api/protected",
            headers={"Authorization": "Bearer  test-secret-token"},
        )
        assert response.status_code == 401


class TestMalformedAuthHeader:
    def test_missing_bearer_prefix_returns_401(self, client):
        response = client.get(
            "/api/protected",
            headers={"Authorization": "test-secret-token"},
        )
        assert response.status_code == 401

    def test_basic_auth_scheme_returns_401(self, client):
        response = client.get(
            "/api/protected",
            headers={"Authorization": "Basic dGVzdA=="},
        )
        assert response.status_code == 401

    def test_bearer_lowercase_returns_401(self, client):
        """Only 'Bearer ' (capital B) is accepted."""
        response = client.get(
            "/api/protected",
            headers={"Authorization": "bearer test-secret-token"},
        )
        assert response.status_code == 401


class TestServerNotConfigured:
    def test_missing_app_token_returns_500(self):
        """When APP_TOKEN is empty (not configured), return 500."""
        app = _create_test_app()
        app.dependency_overrides[get_app_token] = lambda: ""
        client = TestClient(app)

        response = client.get(
            "/api/protected",
            headers={"Authorization": "Bearer some-token"},
        )
        assert response.status_code == 500


class TestHealthEndpointUnprotected:
    def test_health_no_auth_required(self):
        """Health endpoint must work without any auth header."""
        from main import app
        client = TestClient(app)
        response = client.get("/api/health")
        assert response.status_code == 200
