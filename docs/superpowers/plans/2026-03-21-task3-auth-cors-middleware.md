# Task 3: 認証ミドルウェア & CORS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add CORS middleware, Bearer token authentication dependency, and Origin check middleware to the FastAPI backend.

**Architecture:** Refactor main.py to use a `create_app()` factory for testability. Add Starlette CORSMiddleware with origins from `CORS_ORIGINS` env var. Create a `verify_token` FastAPI dependency that validates Bearer tokens against `APP_TOKEN` env var. Add a pure ASGI middleware that rejects requests with non-allowed Origin headers (misoperation prevention per §8.2). Health endpoint remains publicly accessible.

**Tech Stack:** FastAPI, Starlette CORSMiddleware, pytest, httpx

**Design Spec References:** §8.2 (認証), §8.3 (CORS), §5.5 (エラーレスポンス)

---

### Task 1: Refactor to App Factory Pattern

Refactor `main.py` so the FastAPI app is created by a `create_app()` function. Keep `app = create_app()` at module level for backward compatibility with existing imports. This is a prerequisite for testable middleware configuration.

**Files:**
- Modify: `backend/main.py`
- Existing tests must continue to pass unchanged

- [ ] **Step 1: Refactor main.py to use create_app()**

Move app creation into a function. Add `get_cors_origins()` helper for DRY origin configuration. Add `import os` at top.

```python
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI

from database import init_db, check_fts5_ngram_support

logger = logging.getLogger("govassist")


def setup_logging() -> None:
    """Configure logging with RotatingFileHandler per §9.1."""
    logger.setLevel(logging.DEBUG)

    # Avoid duplicate handlers on reload
    if logger.handlers:
        return

    logs_dir = Path(__file__).parent / "logs"
    logs_dir.mkdir(exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    # ERROR → error.log + console (max 5 rotations, 10MB each)
    error_handler = RotatingFileHandler(
        logs_dir / "error.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)

    # WARNING+ → app.log + console (max 3 rotations, 10MB each)
    app_handler = RotatingFileHandler(
        logs_dir / "app.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    app_handler.setLevel(logging.WARNING)
    app_handler.setFormatter(formatter)
    logger.addHandler(app_handler)

    # INFO+ → console only
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


def get_cors_origins() -> list[str]:
    """Parse CORS_ORIGINS env var into a list of stripped, non-empty origin strings."""
    raw = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    return [o for o in (origin.strip() for origin in raw.split(",")) if o]


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title="GovAssist API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url=None,
    )

    @application.get("/api/health")
    def health():
        return {"status": "ok", "version": "0.1.0"}

    return application


app = create_app()

# DB 初期化（テーブルが存在しない場合は作成）
init_db()

setup_logging()

# FTS5 ngram トークナイザ対応状況をログ出力
if check_fts5_ngram_support():
    logger.info("FTS5 ngram tokenizer: supported")
else:
    logger.warning("FTS5 ngram tokenizer: NOT supported. Unicode61 will be used as fallback.")
```

- [ ] **Step 2: Run existing tests to verify nothing breaks**

Run: `cd backend && python -m pytest tests/test_main.py -v`
Expected: All 8 existing tests PASS (health, app title, openapi, 404, logging)

- [ ] **Step 3: Commit**

```bash
git add backend/main.py
git commit -m "refactor(backend): extract create_app() factory and get_cors_origins() helper"
```

---

### Task 2: CORS Middleware

Add Starlette CORSMiddleware to `create_app()`. Testable by creating app instances with custom `CORS_ORIGINS` via the factory pattern.

**Files:**
- Modify: `backend/main.py`
- Create: `backend/tests/test_cors.py`

- [ ] **Step 1: Write CORS tests**

```python
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
        assert response.status_code == 200
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_cors.py -v`
Expected: FAIL — `create_app() got an unexpected keyword argument 'enable_origin_check'`

- [ ] **Step 3: Add CORS middleware to create_app()**

Modify `backend/main.py` — update `create_app()` signature and add CORS middleware:

```python
from fastapi.middleware.cors import CORSMiddleware


def create_app(enable_origin_check: bool = True) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        enable_origin_check: When False, skip Origin check middleware (for testing).
    """
    application = FastAPI(
        title="GovAssist API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url=None,
    )

    # CORS middleware (inner — runs after Origin check)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(),
        allow_methods=["GET", "POST", "PATCH", "DELETE", "PUT"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    @application.get("/api/health")
    def health():
        return {"status": "ok", "version": "0.1.0"}

    return application
```

- [ ] **Step 4: Run CORS tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_cors.py -v`
Expected: All 11 tests PASS

- [ ] **Step 5: Run all existing tests to ensure no regression**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/main.py backend/tests/test_cors.py
git commit -m "feat(backend): add CORS middleware with configurable origins"
```

---

### Task 3: Bearer Token Auth Dependency

Create a `verify_token` FastAPI dependency that validates the `Authorization: Bearer {token}` header against `APP_TOKEN` from `.env`. The dependency is NOT applied globally — individual routes opt in via `Depends(verify_token)`. Health endpoint remains public.

**Files:**
- Modify: `backend/main.py`
- Create: `backend/tests/test_auth.py`

- [ ] **Step 1: Write auth dependency tests**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_auth.py -v`
Expected: FAIL — `ImportError: cannot import name 'verify_token' from 'main'`

- [ ] **Step 3: Implement auth dependency in main.py**

Add imports and functions to `backend/main.py`:

```python
from fastapi import Depends, HTTPException, Request


def get_app_token() -> str:
    """Retrieve the APP_TOKEN from environment."""
    return os.getenv("APP_TOKEN", "")


async def verify_token(request: Request, app_token: str = Depends(get_app_token)) -> str:
    """Validate Bearer token from Authorization header.

    Used as a FastAPI dependency: `Depends(verify_token)`.
    Returns the validated token string on success.
    Raises HTTPException on failure.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="認証トークンが不足しています")

    token = auth_header[7:]  # Skip "Bearer " prefix (7 chars)

    if not app_token:
        raise HTTPException(
            status_code=500,
            detail="サーバー設定が不完全です（APP_TOKEN未設定）",
        )

    import hmac
    if not hmac.compare_digest(token, app_token):
        raise HTTPException(status_code=401, detail="認証トークンが一致しません")

    return token
```

- [ ] **Step 4: Run auth tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_auth.py -v`
Expected: All 11 tests PASS

- [ ] **Step 5: Run all tests to ensure no regression**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/main.py backend/tests/test_auth.py
git commit -m "feat(backend): add Bearer token authentication dependency"
```

---

### Task 4: Origin Check Middleware

Add a pure ASGI middleware that rejects requests from non-allowed Origin headers. This is **not** a security measure — it's misoperation prevention per §8.2. Requests without an Origin header (curl, server-to-server) are allowed through.

**Why pure ASGI instead of BaseHTTPMiddleware?** `BaseHTTPMiddleware` has known issues with CORS header propagation and streaming responses. A pure ASGI middleware avoids these problems entirely.

**Files:**
- Modify: `backend/main.py`
- Create: `backend/tests/test_origin_check.py`

- [ ] **Step 1: Write Origin check tests**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_origin_check.py -v`
Expected: FAIL — disallowed origins return 200 (no origin check implemented)

- [ ] **Step 3: Implement Origin check middleware in main.py**

Add the ASGI middleware class and wire it into `create_app()` in `backend/main.py`:

```python
from starlette.responses import JSONResponse


class OriginCheckMiddleware:
    """Pure ASGI middleware: reject requests from non-allowed origins.

    This is NOT a security measure (§8.2). It prevents accidental cross-origin
    requests (誤操作防止). Requests without an Origin header (curl, direct
    API calls) are allowed through.

    Uses pure ASGI instead of BaseHTTPMiddleware to avoid known issues with
    CORS header propagation.
    """

    # Paths exempt from origin checking (developer tools)
    SKIP_PATHS = {"/docs", "/openapi.json", "/redoc"}

    def __init__(self, app, allowed_origins: list[str] | None = None):
        self.app = app
        self.allowed_origins = set(allowed_origins or get_cors_origins())

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            path = scope["path"].split("?")[0]  # Strip query string
            if path not in self.SKIP_PATHS:
                # Extract Origin header from ASGI scope
                origin = None
                for name, value in scope.get("headers", []):
                    if name == b"origin":
                        origin = value.decode("utf-8")
                        break

                if origin and origin not in self.allowed_origins:
                    response = JSONResponse(
                        status_code=403,
                        content={
                            "error": "forbidden",
                            "message": "許可されていないオリジンです",
                        },
                    )
                    await response(scope, receive, send)
                    return

        await self.app(scope, receive, send)
```

Update `create_app()` to add the Origin check middleware. **Middleware order matters** — Origin check is added AFTER CORS so it runs FIRST (outermost):

```python
def create_app(enable_origin_check: bool = True) -> FastAPI:
    application = FastAPI(
        title="GovAssist API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url=None,
    )

    # CORS middleware (inner — runs second)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(),
        allow_methods=["GET", "POST", "PATCH", "DELETE", "PUT"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    # Origin check (outer — runs first, before CORS)
    if enable_origin_check:
        application.add_middleware(OriginCheckMiddleware)

    @application.get("/api/health")
    def health():
        return {"status": "ok", "version": "0.1.0"}

    return application
```

- [ ] **Step 4: Run Origin check tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_origin_check.py -v`
Expected: All 10 tests PASS

- [ ] **Step 5: Run all tests to ensure no regression**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All tests PASS (existing + new)

- [ ] **Step 6: Commit**

```bash
git add backend/main.py backend/tests/test_origin_check.py
git commit -m "feat(backend): add Origin check middleware for misoperation prevention"
```

---

### Final Verification

- [ ] **Step 1: Run full test suite**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All tests PASS (existing 8 + 11 CORS + 11 auth + 10 origin check = 40 total)

- [ ] **Step 2: Verify the app starts correctly**

Run: `cd backend && python -c "from main import app, verify_token, get_app_token, OriginCheckMiddleware, create_app; print('All exports OK')"`
Expected: `All exports OK`

- [ ] **Step 3: Verify middleware order**

Run: `cd backend && python -c "
from main import create_app
app = create_app()
# Print middleware stack (last added = outermost = runs first)
for mw in app.user_middleware:
    print(f'{mw.cls.__name__}: {mw.kwargs}')
"`
Expected output (order matters):
```
OriginCheckMiddleware: {}
CORSMiddleware: {'allow_origins': [...], 'allow_methods': [...], 'allow_headers': [...]}
```

---

### Implementation Notes

1. **Middleware ordering**: In Starlette, `add_middleware()` adds middleware such that the **last added is outermost** (runs first for requests). Origin check is added after CORS so it wraps CORS and runs first.

2. **Why `enable_origin_check` parameter?** CORS tests need to verify CORS headers in isolation without the Origin check rejecting requests first. The parameter defaults to `True` for production use.

3. **Why pure ASGI for Origin check?** `BaseHTTPMiddleware` has known issues with CORS header propagation (it wraps responses and can drop headers). A pure ASGI middleware avoids this entirely with minimal code.

4. **Auth is a dependency, not middleware**: The `verify_token` dependency is applied per-route via `Depends(verify_token)`, not globally. This allows the health endpoint and docs to remain publicly accessible. Routes that need auth will add this dependency in later tasks.

5. **Error response format**: Auth and Origin check use simple HTTPException/detail responses. The full `ErrorResponse` schema with `request_id` (§5.5) will be implemented as a global exception handler in Task 9 (Proofread route).

6. **Token comparison**: Uses `hmac.compare_digest` for timing-safe comparison (defense-in-depth). While timing attacks are not a realistic concern for localhost-only use, it's a one-line improvement with no downsides.

7. **Origin check construction-time config**: `OriginCheckMiddleware` receives `allowed_origins` at construction time (not per-request env read). This avoids redundant parsing and is consistent with how CORS middleware is configured.
