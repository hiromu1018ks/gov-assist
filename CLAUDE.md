# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GovAssist is a personal-use web application for Japanese local government clerical workers to proofread and improve documents (emails, reports, official documents) using AI. **Localhost-only use — no external deployment.**

- **Design spec**: `docs/design.md` (v1.8.0, written in Japanese) — the authoritative source for all requirements
- **Status**: Backend foundation built (app skeleton, auth (disabled for MVP), CORS, DB, schemas, tests). Frontend and API business logic not yet implemented.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 / Vite, plain CSS (no Tailwind) — **not yet created** |
| Backend | Python 3.12 / FastAPI / Uvicorn |
| AI Engine | SAKURA Internet AI Engine (OpenAI-compatible API), default model: Kimi K2.5 |
| Database | SQLite + FTS5 (ngram) via SQLAlchemy, migrations via Alembic |
| File parsing | mammoth.js (.docx), pdf.js (PDF) — client-side |
| Diff computation | diff-match-patch (Python) — server-side |
| Docx export | python-docx — server-side |

## Current Architecture (Backend)

```
backend/
├── main.py                  # App factory (create_app()), auth dependency (disabled for MVP), CORS, OriginCheckMiddleware, logging
├── database.py              # SQLAlchemy engine/session, init_db(), FTS5 ngram detection
├── models.py                # ORM models (History)
├── schemas.py               # Pydantic request/response models, enums
├── routers/                 # API route handlers (empty — not yet implemented)
├── services/                # Business logic (empty — not yet implemented)
├── migrations/versions/     # Alembic migrations (001_create_history)
├── tests/                   # pytest suite with conftest.py (in-memory SQLite, savepoint isolation)
├── logs/                    # Rotating log files (app.log, error.log)
└── data/                    # SQLite database (gitignored)
```

Frontend-backend communication is REST API (JSON) with `X-Request-ID` header on every request.

## Development Commands

All commands run from `backend/` directory (no frontend exists yet):

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload        # Dev server (port 8000)
alembic upgrade head             # Run DB migrations
pytest                           # Run all tests
pytest tests/test_auth.py        # Run single test file
pytest tests/test_auth.py::test_valid_token  # Run single test
pytest -x                        # Stop on first failure
```

Tests use in-memory SQLite with savepoint isolation via `conftest.py` fixtures (`db_engine`, `db_session`).

## Planned API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check (implemented) |
| POST | `/api/proofread` | AI document proofreading |
| GET | `/api/models` | Available AI models |
| GET/POST/PATCH/DELETE | `/api/history[/{id}]` | History CRUD |
| POST | `/api/export/docx` | Generate .docx from corrected text |
| GET/PUT | `/api/settings` | Server-side settings |

Auth: **Disabled for localhost MVP.** Code preserved in comments. See `docs/superpowers/specs/2026-03-22-auth-removal-design.md` for re-enablement.

## Key Backend Patterns

- **`create_app()` factory**: All middleware and routes registered here. `main.py` calls `init_db()` and `setup_logging()` at module level.
- **`OriginCheckMiddleware`**: Pure ASGI middleware (not `BaseHTTPMiddleware`) — rejects non-allowed origins with 403. Skips `/docs`, `/openapi.json`, `/redoc`. Requests without `Origin` header are allowed.
- **Auth dependency `verify_token()`**: **Currently disabled (commented out) for localhost MVP.** Returns 401 for invalid/missing tokens, 500 if `APP_TOKEN` is not configured. Health endpoint is unprotected.
- **Database URL**: Read from `DATABASE_URL` env var, defaults to `backend/data/govassist.db`.
- **Pydantic schemas**: `DocumentType` enum (email/report/official/other), `ProofreadStatus` (success/partial/error), `DiffType` (equal/insert/delete). Request text limited to 1-8000 chars.

## Critical Design Constraints

These are non-negotiable architectural rules from the design spec:

1. **AI output is never blindly trusted** — JSON parsing, validation, and fallback must all happen server-side (backend services)
2. **Frontend must NOT reconstruct `corrected_text` from diffs** — diffs are for highlight/comparison display only; `corrected_text` is used as-is for copy/download
3. **Frontend renders diffs in reduce-style sequential order** — `start` index is not used for rendering; only array order matters
4. **localStorage is treated as cache** — includes schema versioning (`version: 1`) for future migration
5. **No dangerouslySetInnerHTML** — all rendering via standard React data binding (use DOMPurify if sanitization needed)
6. **No Tailwind** — plain CSS only

## Environment Variables

Backend `.env` (see `.env.example`):
- `CORS_ORIGINS` — comma-separated, default `http://localhost:5173`
- `AI_ENGINE_API_KEY` — SAKURA AI Engine API key
- `APP_TOKEN` — simple auth token for API access (currently disabled, commented out in `.env.example`)
- `DATABASE_URL` — optional override (default: `sqlite:///data/govassist.db`)

## Key Limits

- Input text: max 8,000 characters per proofreading request
- History: default 50 items (configurable 1-200), 20MB SQLite size limit with auto-cleanup
- Result JSON: max 100KB per record (truncated with flag if exceeded)
- AI response retry: up to 3 retries with re-prompting, then fallback
