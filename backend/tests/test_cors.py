# backend/tests/test_cors.py
"""Tests for CORS middleware configuration (§8.3)."""
import os
import pytest
from fastapi.testclient import TestClient

from main import create_app


@pytest.fixture
def client():
    """Create a test client with known CORS origins (no origin check middleware)."""
    os.environ["CORS_ORIGINS"] = "http://localhost:5173,http://localhost:3000"
    app = create_app(enable_origin_check=False)
    return TestClient(app)


class TestCORSAllowedOrigins:
    def test_preflight_for_allowed_origin(self, client):
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:5173"

    def test_preflight_for_second_allowed_origin(self, client):
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"

    def test_simple_request_gets_cors_header(self, client):
        response = client.get(
            "/api/health",
            headers={"Origin": "http://localhost:5173"},
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


class TestCORSRejectedOrigins:
    def test_preflight_for_disallowed_origin_no_header(self, client):
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://evil.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 400
        assert "access-control-allow-origin" not in response.headers

    def test_simple_request_for_disallowed_origin_no_header(self, client):
        response = client.get(
            "/api/health",
            headers={"Origin": "http://evil.com"},
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" not in response.headers


class TestCORSAllowedMethods:
    def test_post_method_allowed(self, client):
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert response.status_code == 200
        assert "POST" in response.headers["access-control-allow-methods"]

    def test_delete_method_allowed(self, client):
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "DELETE",
            },
        )
        assert response.status_code == 200
        assert "DELETE" in response.headers["access-control-allow-methods"]

    def test_patch_method_allowed(self, client):
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "PATCH",
            },
        )
        assert response.status_code == 200
        assert "PATCH" in response.headers["access-control-allow-methods"]


class TestCORSAllowedHeaders:
    def test_authorization_header_allowed(self, client):
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization",
            },
        )
        assert response.status_code == 200
        assert "authorization" in response.headers["access-control-allow-headers"].lower()

    def test_content_type_header_allowed(self, client):
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        assert response.status_code == 200
        assert "content-type" in response.headers["access-control-allow-headers"].lower()

    def test_x_request_id_header_allowed(self, client):
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "X-Request-ID",
            },
        )
        assert response.status_code == 200
        assert "x-request-id" in response.headers["access-control-allow-headers"].lower()


class TestCORSDefaults:
    def test_default_origin_when_env_not_set(self):
        """When CORS_ORIGINS is not set, defaults to http://localhost:5173."""
        os.environ.pop("CORS_ORIGINS", None)
        app = create_app(enable_origin_check=False)
        client = TestClient(app)
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:5173"

    def test_strips_whitespace_from_origins(self):
        """CORS_ORIGINS with spaces around commas are handled correctly."""
        os.environ["CORS_ORIGINS"] = "http://localhost:5173 , http://localhost:3000"
        app = create_app(enable_origin_check=False)
        client = TestClient(app)
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
