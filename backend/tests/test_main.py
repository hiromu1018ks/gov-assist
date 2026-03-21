import logging
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_health_includes_version(self, client):
        resp = client.get("/api/health")
        data = resp.json()
        assert "version" in data


class TestAppConfig:
    def test_app_title(self):
        from main import app
        assert app.title == "GovAssist API"

    def test_app_has_openapi(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200


class Test404:
    def test_unknown_endpoint_returns_404(self, client):
        resp = client.get("/api/nonexistent")
        assert resp.status_code == 404


class TestLoggingSetup:
    """Test that setup_logging() configures handlers per §9.1."""

    def test_setup_logging_creates_three_handlers(self):
        import main
        logger = logging.getLogger("govassist")
        handler_types = [type(h).__name__ for h in logger.handlers]
        assert "RotatingFileHandler" in handler_types
        assert "StreamHandler" in handler_types
        # At least: 1 error file handler, 1 app file handler, 1 console
        assert len(logger.handlers) >= 3

    def test_error_handler_level(self):
        import main
        logger = logging.getLogger("govassist")
        error_handlers = [
            h for h in logger.handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
            and h.level == logging.ERROR
        ]
        assert len(error_handlers) >= 1

    def test_warning_handler_level(self):
        import main
        logger = logging.getLogger("govassist")
        warning_handlers = [
            h for h in logger.handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
            and h.level == logging.WARNING
        ]
        assert len(warning_handlers) >= 1

    def test_console_handler_level(self):
        import main
        logger = logging.getLogger("govassist")
        console_handlers = [
            h for h in logger.handlers
            if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        assert len(console_handlers) >= 1
        assert console_handlers[0].level == logging.INFO
