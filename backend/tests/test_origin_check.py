# backend/tests/test_origin_check.py
"""Tests for Origin check middleware (§8.2 — 誤操作防止)."""
import os
import pytest
from fastapi.testclient import TestClient

from main import create_app


@pytest.fixture
def client():
    os.environ["CORS_ORIGINS"] = "http://localhost:5173,http://localhost:3000"
    app = create_app()
    return TestClient(app)


class TestAllowedOrigins:
    def test_first_allowed_origin_passes(self, client):
        response = client.get(
            "/api/health",
            headers={"Origin": "http://localhost:5173"},
        )
        assert response.status_code == 200

    def test_second_allowed_origin_passes(self, client):
        response = client.get(
            "/api/health",
            headers={"Origin": "http://localhost:3000"},
        )
        assert response.status_code == 200

    def test_preflight_for_allowed_origin_passes(self, client):
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200


class TestDisallowedOrigins:
    def test_disallowed_origin_returns_403(self, client):
        response = client.get(
            "/api/health",
            headers={"Origin": "http://evil.com"},
        )
        assert response.status_code == 403

    def test_disallowed_origin_preflight_returns_403(self, client):
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://evil.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 403

    def test_disallowed_origin_error_body(self, client):
        response = client.get(
            "/api/health",
            headers={"Origin": "http://evil.com"},
        )
        assert response.status_code == 403
        data = response.json()
        assert "message" in data


class TestMissingOrigin:
    def test_no_origin_header_allowed(self, client):
        """Requests without Origin (curl, server-to-server) must pass."""
        # TestClient does not send Origin by default
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_empty_origin_header_allowed(self, client):
        """An empty Origin header is treated as missing."""
        response = client.get("/api/health", headers={"Origin": ""})
        assert response.status_code == 200


class TestDocsEndpoint:
    def test_docs_without_origin_allowed(self, client):
        """Swagger UI (/docs) should be accessible without Origin check."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_docs_with_allowed_origin(self, client):
        response = client.get("/docs", headers={"Origin": "http://localhost:5173"})
        assert response.status_code == 200

    def test_openapi_json_without_origin(self, client):
        """OpenAPI schema should be accessible without Origin check."""
        response = client.get("/openapi.json")
        assert response.status_code == 200


class TestDefaultOrigin:
    def test_default_origin_when_env_not_set(self):
        os.environ.pop("CORS_ORIGINS", None)
        app = create_app()
        client = TestClient(app)
        response = client.get(
            "/api/health",
            headers={"Origin": "http://localhost:5173"},
        )
        assert response.status_code == 200
