# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GovAssist is a personal-use web application for Japanese local government clerical workers to proofread and improve documents (emails, reports, official documents) using AI. **Localhost-only use — no external deployment.**

- **Design spec**: `docs/design.md` (v1.8.0, written in Japanese) — the authoritative source for all requirements
- **Status**: Pre-implementation — only the design document exists

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 / Vite, plain CSS (no Tailwind) |
| Backend | Python 3.12 / FastAPI / Uvicorn |
| AI Engine | SAKURA Internet AI Engine (OpenAI-compatible API), default model: Kimi K2.5 |
| Database | SQLite + FTS5 (ngram) via SQLAlchemy, migrations via Alembic |
| File parsing | mammoth.js (.docx), pdf.js (PDF) — client-side |
| Diff computation | diff-match-patch (Python) — server-side |
| Docx export | python-docx — server-side |

## Architecture

```
govassist/
├── frontend/                    # React (Vite)
│   └── src/
│       ├── components/          # Shared UI (SideMenu, Header, common/)
│       └── tools/               # Feature modules (each tool = subdirectory)
│           ├── proofreading/    # Main tool: InputArea, OptionPanel, ResultView, DiffView, preprocess.js
│           ├── history/         # Proofreading history browser
│           └── settings/        # App settings
└── backend/                     # Python (FastAPI)
    ├── main.py                  # App entry, routers, CORS
    ├── routers/                 # API route handlers
    └── services/                # Business logic (ai_client, prompt_builder, response_parser, diff_service, docx_exporter)
```

Frontend-backend communication is REST API (JSON) with `X-Request-ID` header on every request.

## Development Commands

### Frontend
```bash
cd frontend
npm install
npm run dev          # Dev server (localhost:5173)
npm run build        # Production build
```

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload   # Dev server
alembic upgrade head        # Run DB migrations
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/proofread` | AI document proofreading |
| GET | `/api/models` | Available AI models |
| GET/POST/PATCH/DELETE | `/api/history[/{id}]` | History CRUD |
| POST | `/api/export/docx` | Generate .docx from corrected text |
| GET/PUT | `/api/settings` | Server-side settings |

Auth: `Authorization: Bearer {token}` (simple fixed token from `.env`).

## Critical Design Constraints

These are non-negotiable architectural rules from the design spec:

1. **AI output is never blindly trusted** — JSON parsing, validation, and fallback must all happen server-side (backend services)
2. **Frontend must NOT reconstruct `corrected_text` from diffs** — diffs are for highlight/comparison display only; `corrected_text` is used as-is for copy/download
3. **Frontend renders diffs in reduce-style sequential order** — `start` index is not used for rendering; only array order matters
4. **localStorage is treated as cache** — includes schema versioning (`version: 1`) for future migration
5. **No `dangerouslySetInnerHTML`** — all rendering via standard React data binding (use DOMPurify if sanitization needed)
6. **No Tailwind** — plain CSS only

## Environment Variables

Backend `.env` (see `.env.example`):
- `CORS_ORIGINS` — default `http://localhost:5173`
- `AI_ENGINE_API_KEY` — SAKURA AI Engine API key
- `APP_TOKEN` — simple auth token for API access

## Key Limits

- Input text: max 8,000 characters per proofreading request
- History: default 50 items (configurable 1–200), 20MB SQLite size limit with auto-cleanup
- Result JSON: max 100KB per record (truncated with flag if exceeded)
- AI response retry: up to 3 retries with re-prompting, then fallback
