# Task 1: バックエンドプロジェクトセットアップ Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the FastAPI backend project foundation with Pydantic schemas, logging configuration, and app skeleton.

**Architecture:** FastAPI app with modular Pydantic schemas for all API request/response types. Logging uses Python's RotatingFileHandler with separate handlers per level. The app skeleton is minimal — routers will be added in later tasks.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, Uvicorn, pytest

**Design Spec References:** §2.2 (tech stack), §4.6 (response JSON), §5.2–5.5 (API specs), §9 (logging), §11 (directory structure)

---

## File Structure

```
backend/
├── requirements.txt          # Python dependencies
├── main.py                   # FastAPI app entry, logging setup, router registration
├── schemas.py                # All Pydantic models (request/response/error)
├── .env.example              # Environment variable template
├── .gitignore                # Python gitignore (logs/, __pycache__/, .env)
├── logs/
│   └── .gitkeep              # Keep empty dir in git
└── tests/
    ├── __init__.py
    ├── conftest.py           # Shared fixtures
    ├── test_schemas.py       # Pydantic schema validation tests
    └── test_main.py          # App startup, health endpoint, and logging tests
```

---

### Task 1: Project scaffolding & dependencies

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/.gitignore`
- Create: `backend/logs/.gitkeep`
- Create: `backend/tests/__init__.py`

- [ ] **Step 1: Create backend directory structure**

```bash
mkdir -p backend/logs backend/tests backend/routers backend/services backend/migrations
touch backend/logs/.gitkeep
touch backend/tests/__init__.py
touch backend/routers/__init__.py
touch backend/services/__init__.py
touch backend/migrations/__init__.py
```

- [ ] **Step 2: Create `backend/requirements.txt`**

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
pydantic==2.10.4
pydantic-settings==2.7.1
httpx==0.28.1
python-multipart==0.0.20
```

> Note: Additional deps (sqlalchemy, alembic, diff-match-patch, python-docx, openai) will be added in later tasks as needed.

- [ ] **Step 3: Create `backend/.env.example`**

```
# SAKURA Internet AI Engine API Key
AI_ENGINE_API_KEY=your-api-key-here

# Simple auth token for API access
APP_TOKEN=change-me-to-a-secure-token

# CORS allowed origins (comma-separated)
CORS_ORIGINS=http://localhost:5173
```

- [ ] **Step 4: Create `backend/.gitignore`**

```
__pycache__/
*.py[cod]
*$py.class
.env
logs/*.log
*.egg-info/
dist/
build/
.pytest_cache/
.mypy_cache/
```

- [ ] **Step 5: Install dependencies and verify**

```bash
cd backend
pip install -r requirements.txt
python -c "import fastapi; import pydantic; import uvicorn; print('OK')"
```

Expected output: `OK`

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "chore: scaffold backend project structure with dependencies"
```

---

### Task 2: Pydantic schemas

**Files:**
- Create: `backend/schemas.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_schemas.py`

- [ ] **Step 1: Write failing tests for schemas**

Create `backend/tests/conftest.py`:

```python
import pytest
```

Create `backend/tests/test_schemas.py`:

```python
import pytest
from schemas import (
    DocumentType,
    ProofreadOptions,
    ProofreadRequest,
    CorrectionItem,
    DiffBlock,
    DiffType,
    ProofreadResponse,
    ProofreadStatus,
    StatusReason,
    ErrorResponse,
    ExportDocxRequest,
)


class TestDocumentType:
    def test_valid_types(self):
        assert DocumentType.EMAIL == "email"
        assert DocumentType.REPORT == "report"
        assert DocumentType.OFFICIAL == "official"
        assert DocumentType.OTHER == "other"

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError):
            DocumentType("invalid")


class TestProofreadOptions:
    def test_all_true(self):
        opts = ProofreadOptions(
            typo=True, keigo=True, terminology=True,
            style=True, legal=True, readability=True,
        )
        assert opts.typo is True
        assert opts.legal is True

    def test_defaults(self):
        opts = ProofreadOptions()
        assert opts.typo is True
        assert opts.keigo is True
        assert opts.terminology is True
        assert opts.style is True
        assert opts.legal is False
        assert opts.readability is True


class TestProofreadRequest:
    def test_valid_request(self):
        req = ProofreadRequest(
            request_id="test-uuid",
            text="テスト文章",
            document_type=DocumentType.OFFICIAL,
            model="kimi-k2.5",
        )
        assert req.text == "テスト文章"
        assert req.document_type == DocumentType.OFFICIAL
        assert req.model == "kimi-k2.5"
        assert req.request_id == "test-uuid"

    def test_default_model(self):
        req = ProofreadRequest(
            request_id="test-uuid",
            text="テスト",
            document_type=DocumentType.EMAIL,
        )
        assert req.model == "kimi-k2.5"

    def test_text_max_length(self):
        long_text = "あ" * 8001
        with pytest.raises(ValueError):
            ProofreadRequest(
                request_id="test-uuid",
                text=long_text,
                document_type=DocumentType.EMAIL,
            )

    def test_text_empty_raises(self):
        with pytest.raises(ValueError):
            ProofreadRequest(
                request_id="test-uuid",
                text="",
                document_type=DocumentType.EMAIL,
            )


class TestProofreadResponse:
    def test_success_response(self):
        resp = ProofreadResponse(
            request_id="test-uuid",
            status=ProofreadStatus.SUCCESS,
            corrected_text="校正済みテキスト",
            summary="3件の修正を行いました。",
            corrections=[],
            diffs=[],
        )
        assert resp.status == "success"
        assert resp.status_reason is None
        assert resp.warnings == []

    def test_partial_response(self):
        resp = ProofreadResponse(
            request_id="test-uuid",
            status=ProofreadStatus.PARTIAL,
            status_reason=StatusReason.DIFF_TIMEOUT,
            corrected_text="テキスト",
        )
        assert resp.status == "partial"
        assert resp.status_reason == "diff_timeout"

    def test_error_response(self):
        resp = ProofreadResponse(
            request_id="test-uuid",
            status=ProofreadStatus.ERROR,
            status_reason=StatusReason.PARSE_FALLBACK,
            corrected_text="",
        )
        assert resp.status == "error"
        assert resp.status_reason == "parse_fallback"

    def test_large_rewrite_warning(self):
        resp = ProofreadResponse(
            request_id="test-uuid",
            status=ProofreadStatus.SUCCESS,
            corrected_text="テキスト",
            warnings=["large_rewrite"],
        )
        assert resp.warnings == ["large_rewrite"]


class TestCorrectionItem:
    def test_valid_correction(self):
        item = CorrectionItem(
            original="修正前",
            corrected="修正後",
            reason="誤字のため",
            category="誤字脱字",
            diff_matched=True,
        )
        assert item.diff_matched is True

    def test_defaults(self):
        item = CorrectionItem(
            original="修正前",
            corrected="修正後",
            reason="理由",
            category="用語",
        )
        assert item.diff_matched is False


class TestDiffBlock:
    def test_equal_block(self):
        block = DiffBlock(
            type=DiffType.EQUAL,
            text="テキスト",
            start=0,
        )
        assert block.position is None
        assert block.reason is None

    def test_insert_block(self):
        block = DiffBlock(
            type=DiffType.INSERT,
            text="追加",
            start=5,
            position="after",
            reason="理由",
        )
        assert block.position == "after"

    def test_delete_block(self):
        block = DiffBlock(
            type=DiffType.DELETE,
            text="削除",
            start=5,
            reason="理由",
        )
        assert block.position is None

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError):
            DiffBlock(
                type="invalid",
                text="テキスト",
                start=0,
            )


class TestErrorResponse:
    def test_error_response(self):
        err = ErrorResponse(
            request_id="test-uuid",
            error="text_too_long",
            message="入力文字数が上限を超えています。",
        )
        assert err.error == "text_too_long"


class TestExportDocxRequest:
    def test_valid_request(self):
        req = ExportDocxRequest(
            corrected_text="校正済みテキスト",
            document_type=DocumentType.OFFICIAL,
        )
        assert req.corrected_text == "校正済みテキスト"

    def test_empty_text_raises(self):
        with pytest.raises(ValueError):
            ExportDocxRequest(
                corrected_text="",
                document_type=DocumentType.OFFICIAL,
            )
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
python -m pytest tests/test_schemas.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'schemas'`

- [ ] **Step 3: Implement `backend/schemas.py`**

```python
from enum import Enum
from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    EMAIL = "email"
    REPORT = "report"
    OFFICIAL = "official"
    OTHER = "other"


class ProofreadStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    ERROR = "error"


class StatusReason(str, Enum):
    DIFF_TIMEOUT = "diff_timeout"
    PARSE_FALLBACK = "parse_fallback"


class DiffType(str, Enum):
    EQUAL = "equal"
    INSERT = "insert"
    DELETE = "delete"


class ProofreadOptions(BaseModel):
    typo: bool = True
    keigo: bool = True
    terminology: bool = True
    style: bool = True
    legal: bool = False
    readability: bool = True


class ProofreadRequest(BaseModel):
    request_id: str
    text: str = Field(min_length=1, max_length=8000)
    document_type: DocumentType
    options: ProofreadOptions = ProofreadOptions()
    model: str = "kimi-k2.5"


class CorrectionItem(BaseModel):
    original: str
    corrected: str
    reason: str
    category: str
    diff_matched: bool = False


class DiffBlock(BaseModel):
    type: DiffType
    text: str
    start: int
    position: str | None = None
    reason: str | None = None


class ProofreadResponse(BaseModel):
    request_id: str
    status: ProofreadStatus
    status_reason: StatusReason | None = None
    warnings: list[str] = []
    corrected_text: str
    summary: str | None = None
    corrections: list[CorrectionItem] = []
    diffs: list[DiffBlock] = []


class ErrorResponse(BaseModel):
    request_id: str
    error: str
    message: str


class ExportDocxRequest(BaseModel):
    corrected_text: str = Field(min_length=1)
    document_type: DocumentType
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
python -m pytest tests/test_schemas.py -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/schemas.py backend/tests/
git commit -m "feat(backend): add Pydantic schemas for all API request/response types"
```

---

### Task 3: FastAPI app skeleton & logging

**Files:**
- Create: `backend/main.py`
- Create: `backend/tests/test_main.py`

> **§9.1 ログ保持期間について**: 設計書では error.log 30日・app.log 7日の保持期間が規定されているが、`RotatingFileHandler` はファイル数ベースのローテーションのみ対応。localhost 個人利用の MVP ではファイル数ベース（error 5世代・app 3世代）で十分と判断し、時間ベース保持期間は将来拡張とする。

- [ ] **Step 1: Write failing tests for app startup and logging**

Create `backend/tests/test_main.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
python -m pytest tests/test_main.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'main'`

> Note: logging tests will also fail since `setup_logging()` doesn't exist yet.

- [ ] **Step 3: Implement `backend/main.py`**

```python
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI

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


app = FastAPI(
    title="GovAssist API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
)


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


setup_logging()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
python -m pytest tests/test_main.py -v
```

Expected: All tests PASS

- [ ] **Step 5: Verify server starts manually**

```bash
cd backend
timeout 3 uvicorn main:app --host 127.0.0.1 --port 8000 || true
```

Expected: Server starts without errors, shows `Uvicorn running on http://127.0.0.1:8000`

- [ ] **Step 6: Commit**

```bash
git add backend/main.py backend/tests/test_main.py
git commit -m "feat(backend): add FastAPI app skeleton with health endpoint and logging"
```

---

### Task 4: Run full test suite & final verification

**Files:** None (verification only)

- [ ] **Step 1: Run all tests**

```bash
cd backend
python -m pytest tests/ -v
```

Expected: All tests PASS (test_schemas, test_main)

- [ ] **Step 2: Verify no log files are tracked by git**

```bash
cd backend
git status
```

Expected: `logs/*.log` files should NOT appear (covered by `.gitignore`)

- [ ] **Step 3: Verify directory structure matches design spec §11**

```bash
ls -la backend/
ls -la backend/routers/
ls -la backend/services/
ls -la backend/migrations/
ls -la backend/logs/
```

Expected: All directories exist with `__init__.py` where needed

---

## Summary

| Task | What | Tests |
|------|------|-------|
| 1 | Project scaffolding, deps, .env | Manual verification |
| 2 | Pydantic schemas | 15 schema validation tests |
| 3 | FastAPI app skeleton + logging | 9 app/logging tests |
| 4 | Full suite verification | All 24 tests pass |
