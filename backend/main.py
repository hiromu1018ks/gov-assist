import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from database import init_db, check_fts5_ngram_support
from dependencies import verify_token, get_app_token

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

    # Origin check (outer — runs first, before CORS)
    if enable_origin_check:
        application.add_middleware(OriginCheckMiddleware)

    @application.get("/api/health")
    def health():
        return {"status": "ok", "version": "0.1.0"}

    from routers.models_router import router as models_router
    application.include_router(models_router)

    from routers.settings import router as settings_router
    application.include_router(settings_router)

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
