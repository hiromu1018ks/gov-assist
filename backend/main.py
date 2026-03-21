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
