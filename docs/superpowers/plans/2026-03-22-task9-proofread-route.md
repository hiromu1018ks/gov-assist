# Task 9: Proofread Route Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement POST /api/proofread endpoint that orchestrates AI client, prompt builder, response parser, and diff service into a complete proofreading pipeline.

**Architecture:** Single router file `backend/routers/proofread.py` with one async endpoint. Orchestrates four existing services: `get_model_config()` + `create_ai_client()` from ai_client, `build_prompts()` from prompt_builder, `parse_ai_response()` from response_parser, and `compute_diffs()` from diff_service. Error responses use `JSONResponse` with ErrorResponse schema per §5.5. Success responses use `ProofreadResponse`. Tests mock individual service functions at the router module level for clean unit testing.

**Tech Stack:** FastAPI, unittest.mock (patch/AsyncMock), Starlette JSONResponse

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `backend/routers/proofread.py` | POST /api/proofread endpoint — full orchestration of AI → parse → diff pipeline |
| Create | `backend/tests/test_proofread.py` | Unit tests with mocked services (~15 test cases) |
| Modify | `backend/main.py:138-142` | Register proofread router (add 2 lines after existing router registrations) |

### Key Interfaces (already implemented, do NOT modify)

**`services/ai_client.py`**
- `get_model_config(model_id: str) -> ModelConfig` — raises `KeyError` for unknown model
- `create_ai_client() -> AIClient` — reads env vars, raises `ValueError` if not set
- `AIClient.complete(model, system_prompt, user_prompt, max_tokens, temperature, request_id) -> str` — async, raises `AIClientError`
- `AIClientError(error_code: str, message: str)` — codes: `ai_timeout`, `ai_rate_limit`, `ai_invalid_response`

**`services/prompt_builder.py`**
- `build_prompts(request: ProofreadRequest) -> tuple[str, str]` — returns (system_prompt, user_prompt)

**`services/response_parser.py`**
- `parse_ai_response(*, raw_response, ai_client, model, system_prompt, user_prompt, request_id, max_tokens, temperature) -> ParseResult` — async, handles retry/fallback
- `ParseResult(corrected_text, summary, corrections, status, status_reason)` — status: SUCCESS/PARTIAL/ERROR

**`services/diff_service.py`**
- `compute_diffs(*, input_text, corrected_text, corrections, request_id, enable_diff_compaction=True) -> DiffResult` — sync
- `DiffResult(diffs, warnings, status, status_reason, corrections)` — warnings may contain `"large_rewrite"`

### Status Logic (critical — implement exactly)

```
parse status = ERROR    → HTTP 502 ErrorResponse (ai_parse_error)
parse status = PARTIAL  → HTTP 200 ProofreadResponse (no diffs computed)
parse status = SUCCESS  → compute_diffs()
  diff status = SUCCESS  → HTTP 200 ProofreadResponse (status=success)
  diff status = PARTIAL  → HTTP 200 ProofreadResponse (status=partial, status_reason=diff_timeout)
```

### Error Mapping (§5.5)

| Condition | HTTP | error code | message |
|-----------|------|------------|---------|
| Unknown model | 400 | `validation_error` | 指定されたモデルが見つかりません: {model} |
| AIClientError ai_timeout | 504 | `ai_timeout` | AI応答がタイムアウトしました（60秒） |
| AIClientError ai_rate_limit | 502 | `ai_rate_limit` | AI APIのレート制限に達しました |
| AIClientError ai_invalid_response | 502 | `ai_invalid_response` | AI API エラーが発生しました |
| Parse ERROR status | 502 | `ai_parse_error` | 校正結果を解析できませんでした |
| Unexpected exception | 500 | `internal_error` | サーバー内部エラーが発生しました |

### Large Rewrite Handling (§4.4 step 10)

When `diff_result.warnings` contains `"large_rewrite"`, append to summary:
- If summary exists: `summary + "\n\n" + LARGE_REWRITE_SUMMARY`
- If summary is None: just `LARGE_REWRITE_SUMMARY`
- `LARGE_REWRITE_SUMMARY = "⚠️ AI が広範囲を書き換えました。内容を十分ご確認ください。"`

### Design Decisions (deviations from spec documented)

1. **`text_too_long` (§5.5):** The spec defines `400 text_too_long` for input exceeding 8,000 characters. However, Pydantic's `max_length=8000` on `ProofreadRequest.text` already rejects overlong text with HTTP 422. This is functionally equivalent and provides clear validation error messages. Adding a separate 400 handler would require a custom exception handler that duplicates Pydantic's validation. **Accepted deviation: 422 instead of 400 for text length.**

2. **Unknown AI error codes:** When `AIClientError` has an unrecognized `error_code`, the router maps it to `"ai_invalid_response"` (not the raw unknown code) to prevent leaking undocumented error codes to the frontend.

---

## Task 1: Router Skeleton + Auth + Validation

**Files:**
- Create: `backend/routers/proofread.py`
- Modify: `backend/main.py`
- Test: `backend/tests/test_proofread.py`

- [ ] **Step 1: Create router skeleton**

Create `backend/routers/proofread.py`:

```python
"""POST /api/proofread — AI 文書校正の実行 (§4.4, §5.2, §5.5)."""
import logging

from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse

from dependencies import verify_token
from schemas import (
    ErrorResponse,
    ProofreadRequest,
    ProofreadResponse,
)
from services.ai_client import get_model_config

logger = logging.getLogger("govassist")

router = APIRouter(prefix="/api", tags=["proofread"])


def _error_json(request_id: str, error: str, message: str, status: int) -> JSONResponse:
    """Build a JSON error response per §5.5."""
    return JSONResponse(
        status_code=status,
        content=ErrorResponse(
            request_id=request_id,
            error=error,
            message=message,
        ).model_dump(),
    )


@router.post("/proofread", response_model=ProofreadResponse)
async def proofread(
    payload: ProofreadRequest,
    token: str = Depends(verify_token),
):
    """AI 文書校正を実行する (§4.4, §5.2)."""
    request_id = payload.request_id

    # Validate model exists
    try:
        get_model_config(payload.model)
    except KeyError:
        return _error_json(
            request_id,
            "validation_error",
            f"指定されたモデルが見つかりません: {payload.model}",
            400,
        )

    # TODO: implement pipeline (Task 2+)
    return ProofreadResponse(
        request_id=request_id,
        status="success",
        corrected_text=payload.text,
    )
```

- [ ] **Step 2: Register router in main.py**

Add to `backend/main.py` after the settings router registration (after line 142):

```python
    from routers.proofread import router as proofread_router
    application.include_router(proofread_router)
```

- [ ] **Step 3: Write failing tests for auth + validation**

Create `backend/tests/test_proofread.py`:

```python
"""Tests for POST /api/proofread endpoint (§4.4, §5.2, §5.5)."""
import pytest
from unittest.mock import patch

from services.ai_client import ModelConfig

VALID_REQUEST = {
    "request_id": "test-req-001",
    "text": "これはテスト文書です。誤字があります。",
    "document_type": "official",
    "options": {
        "typo": True,
        "keigo": True,
        "terminology": True,
        "style": True,
        "legal": False,
        "readability": True,
    },
    "model": "kimi-k2.5",
}

AUTH_HEADERS = {"Authorization": "Bearer test-secret-token"}

MOCK_MODEL_CONFIG = ModelConfig(
    display_name="Kimi K2.5",
    max_tokens=4096,
    temperature=0.3,
    max_input_chars=8000,
    json_forced=True,
)


@pytest.fixture
def client(app_client):
    return app_client


class TestAuthAndValidation:
    def test_requires_auth(self, client):
        resp = client.post("/api/proofread", json=VALID_REQUEST)
        assert resp.status_code == 401

    def test_rejects_wrong_token(self, client):
        resp = client.post(
            "/api/proofread",
            json=VALID_REQUEST,
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert resp.status_code == 401

    @patch("routers.proofread.get_model_config")
    def test_unknown_model_returns_400(self, mock_config, client):
        mock_config.side_effect = KeyError("unknown-model")
        resp = client.post(
            "/api/proofread",
            json={**VALID_REQUEST, "model": "nonexistent-model"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data["error"] == "validation_error"
        assert "nonexistent-model" in data["message"]
        assert data["request_id"] == "test-req-001"

    @patch("routers.proofread.get_model_config")
    def test_valid_model_passes_validation(self, mock_config, client):
        mock_config.return_value = MOCK_MODEL_CONFIG
        resp = client.post("/api/proofread", json=VALID_REQUEST, headers=AUTH_HEADERS)
        # Currently returns 200 with stub response; will be refined in Task 2
        assert resp.status_code == 200

    def test_empty_text_returns_422(self, client):
        resp = client.post(
            "/api/proofread",
            json={**VALID_REQUEST, "text": ""},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 422

    def test_text_over_8000_chars_returns_422(self, client):
        resp = client.post(
            "/api/proofread",
            json={**VALID_REQUEST, "text": "あ" * 8001},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 422
```

- [ ] **Step 4: Run tests to verify they pass (skeleton already handles auth + validation)**

Run: `cd backend && pytest tests/test_proofread.py -v`
Expected: All 6 tests PASS (auth is handled by `verify_token` dependency, model validation is implemented, Pydantic handles text validation)

- [ ] **Step 5: Commit**

```bash
git add backend/routers/proofread.py backend/tests/test_proofread.py backend/main.py
git commit -m "feat(backend): add proofread route skeleton with auth and model validation

- Create routers/proofread.py with POST /api/proofread endpoint
- Add model validation (400 for unknown model)
- Register proofread router in main.py
- Add 6 unit tests for auth and validation"
```

---

## Task 2: Success Path

**Files:**
- Modify: `backend/routers/proofread.py`
- Modify: `backend/tests/test_proofread.py`

- [ ] **Step 1: Write failing test for successful proofread**

Add to `backend/tests/test_proofread.py`:

```python
from unittest.mock import AsyncMock

from schemas import (
    CorrectionItem,
    DiffBlock,
    DiffType,
    ProofreadStatus,
)
from services.diff_service import DiffResult
from services.response_parser import ParseResult


class TestSuccessPath:
    @patch("routers.proofread.compute_diffs")
    @patch("routers.proofread.parse_ai_response", new_callable=AsyncMock)
    @patch("routers.proofread.create_ai_client")
    @patch("routers.proofread.build_prompts")
    @patch("routers.proofread.get_model_config")
    def test_successful_proofread(
        self, mock_config, mock_build, mock_create, mock_parse, mock_diffs, client,
    ):
        mock_config.return_value = MOCK_MODEL_CONFIG
        mock_build.return_value = ("system_prompt", "user_prompt")
        mock_ai = AsyncMock()
        mock_ai.complete.return_value = '{"corrected_text": "...", "summary": "...", "corrections": []}'
        mock_create.return_value = mock_ai
        mock_parse.return_value = ParseResult(
            corrected_text="これはテスト文書です。誤字がありません。",
            summary="1件の修正を行いました。",
            corrections=[
                CorrectionItem(
                    original="あります", corrected="ありません",
                    reason="否定の誤り", category="誤字脱字",
                ),
            ],
            status=ProofreadStatus.SUCCESS,
            status_reason=None,
        )
        mock_diffs.return_value = DiffResult(
            diffs=[
                DiffBlock(type=DiffType.EQUAL, text="これはテスト文書です。誤字が", start=0),
                DiffBlock(type=DiffType.DELETE, text="あり", start=14, reason="否定の誤り"),
                DiffBlock(type=DiffType.INSERT, text="ありません", start=14, position="after", reason="否定の誤り"),
                DiffBlock(type=DiffType.EQUAL, text="。", start=16),
            ],
            warnings=[],
            status=ProofreadStatus.SUCCESS,
            status_reason=None,
            corrections=[
                CorrectionItem(
                    original="あります", corrected="ありません",
                    reason="否定の誤り", category="誤字脱字", diff_matched=True,
                ),
            ],
        )

        resp = client.post("/api/proofread", json=VALID_REQUEST, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["request_id"] == "test-req-001"
        assert data["status"] == "success"
        assert data["status_reason"] is None
        assert data["corrected_text"] == "これはテスト文書です。誤字がありません。"
        assert data["summary"] == "1件の修正を行いました。"
        assert len(data["diffs"]) == 4
        assert data["diffs"][1]["type"] == "delete"
        assert data["diffs"][2]["position"] == "after"
        assert len(data["corrections"]) == 1
        assert data["corrections"][0]["diff_matched"] is True
        assert data["warnings"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_proofread.py::TestSuccessPath::test_successful_proofread -v`
Expected: FAIL — the route returns the stub response, not the full pipeline result

- [ ] **Step 3: Implement the success pipeline**

Replace the TODO section in `backend/routers/proofread.py` with the full pipeline. The complete file should be:

```python
"""POST /api/proofread — AI 文書校正の実行 (§4.4, §5.2, §5.5)."""
import logging

from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse

from dependencies import verify_token
from schemas import (
    ErrorResponse,
    ProofreadRequest,
    ProofreadResponse,
    ProofreadStatus,
)
from services.ai_client import (
    AIClientError,
    create_ai_client,
    get_model_config,
)
from services.diff_service import compute_diffs
from services.prompt_builder import build_prompts
from services.response_parser import parse_ai_response

logger = logging.getLogger("govassist")

router = APIRouter(prefix="/api", tags=["proofread"])

LARGE_REWRITE_SUMMARY = "⚠️ AI が広範囲を書き換えました。内容を十分ご確認ください。"

# §5.5: AI エラーの HTTP ステータスコード・メッセージ対応
_AI_ERROR_MAP: dict[str, tuple[int, str]] = {
    "ai_timeout": (504, "AI応答がタイムアウトしました（60秒）"),
    "ai_rate_limit": (502, "AI APIのレート制限に達しました"),
    "ai_invalid_response": (502, "AI API エラーが発生しました"),
}


def _error_json(request_id: str, error: str, message: str, status: int) -> JSONResponse:
    """Build a JSON error response per §5.5."""
    return JSONResponse(
        status_code=status,
        content=ErrorResponse(
            request_id=request_id,
            error=error,
            message=message,
        ).model_dump(),
    )


@router.post("/proofread", response_model=ProofreadResponse)
async def proofread(
    payload: ProofreadRequest,
    token: str = Depends(verify_token),
):
    """AI 文書校正を実行する (§4.4, §5.2)."""
    request_id = payload.request_id

    # Validate model exists
    try:
        config = get_model_config(payload.model)
    except KeyError:
        return _error_json(
            request_id,
            "validation_error",
            f"指定されたモデルが見つかりません: {payload.model}",
            400,
        )

    try:
        # Build prompts
        system_prompt, user_prompt = build_prompts(payload)

        # Call AI
        ai_client = create_ai_client()
        raw_response = await ai_client.complete(
            model=payload.model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            request_id=request_id,
        )

        # Parse AI response
        parse_result = await parse_ai_response(
            raw_response=raw_response,
            ai_client=ai_client,
            model=payload.model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            request_id=request_id,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
        )

        # Parse complete failure → HTTP 502
        if parse_result.status == ProofreadStatus.ERROR:
            return _error_json(
                request_id,
                "ai_parse_error",
                "校正結果を解析できませんでした",
                502,
            )

        # Parse partial (fallback) → return without diffs
        if parse_result.status == ProofreadStatus.PARTIAL:
            return ProofreadResponse(
                request_id=request_id,
                status=ProofreadStatus.PARTIAL,
                status_reason=parse_result.status_reason,
                warnings=[],
                corrected_text=parse_result.corrected_text,
                summary=parse_result.summary,
                corrections=parse_result.corrections,
                diffs=[],
            )

        # Compute diffs
        diff_result = compute_diffs(
            input_text=payload.text,
            corrected_text=parse_result.corrected_text,
            corrections=parse_result.corrections,
            request_id=request_id,
        )

        # Append large_rewrite warning to summary
        summary = parse_result.summary
        if "large_rewrite" in diff_result.warnings:
            if summary:
                summary = summary + "\n\n" + LARGE_REWRITE_SUMMARY
            else:
                summary = LARGE_REWRITE_SUMMARY

        return ProofreadResponse(
            request_id=request_id,
            status=diff_result.status,
            status_reason=diff_result.status_reason,
            warnings=diff_result.warnings,
            corrected_text=parse_result.corrected_text,
            summary=summary,
            corrections=diff_result.corrections,
            diffs=diff_result.diffs,
        )

    except AIClientError as e:
        status_code, message = _AI_ERROR_MAP.get(
            e.error_code, (502, "AI API エラーが発生しました"),
        )
        # Sanitize unknown error codes to prevent leaking undocumented codes
        error_code = e.error_code if e.error_code in _AI_ERROR_MAP else "ai_invalid_response"
        logger.error(
            "Proofread AI error: request_id=%s error=%s message=%s",
            request_id, e.error_code, e.message,
        )
        return _error_json(request_id, error_code, message, status_code)

    except Exception as e:
        logger.error(
            "Proofread internal error: request_id=%s error=%s",
            request_id, str(e),
            exc_info=True,
        )
        return _error_json(
            request_id,
            "internal_error",
            "サーバー内部エラーが発生しました",
            500,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_proofread.py::TestSuccessPath::test_successful_proofread -v`
Expected: PASS

- [ ] **Step 5: Write failing test for large_rewrite warning**

Add to `TestSuccessPath` class in test file:

```python
    @patch("routers.proofread.compute_diffs")
    @patch("routers.proofread.parse_ai_response", new_callable=AsyncMock)
    @patch("routers.proofread.create_ai_client")
    @patch("routers.proofread.build_prompts")
    @patch("routers.proofread.get_model_config")
    def test_large_rewrite_appends_warning_to_summary(
        self, mock_config, mock_build, mock_create, mock_parse, mock_diffs, client,
    ):
        mock_config.return_value = MOCK_MODEL_CONFIG
        mock_build.return_value = ("s", "u")
        mock_create.return_value = AsyncMock()
        mock_parse.return_value = ParseResult(
            corrected_text="大幅修正テキスト", summary="5件の修正を行いました。",
            corrections=[], status=ProofreadStatus.SUCCESS, status_reason=None,
        )
        mock_diffs.return_value = DiffResult(
            diffs=[], warnings=["large_rewrite"],
            status=ProofreadStatus.SUCCESS, status_reason=None, corrections=[],
        )

        resp = client.post("/api/proofread", json=VALID_REQUEST, headers=AUTH_HEADERS)
        data = resp.json()
        assert data["warnings"] == ["large_rewrite"]
        assert "広範囲を書き換えました" in data["summary"]
        assert "5件の修正を行いました。" in data["summary"]
```

- [ ] **Step 6: Run test to verify it passes (large_rewrite already implemented in Step 3)**

Run: `cd backend && pytest tests/test_proofread.py::TestSuccessPath::test_large_rewrite_appends_warning_to_summary -v`
Expected: PASS

- [ ] **Step 7: Write failing test for large_rewrite with null summary**

Add to `TestSuccessPath` class:

```python
    @patch("routers.proofread.compute_diffs")
    @patch("routers.proofread.parse_ai_response", new_callable=AsyncMock)
    @patch("routers.proofread.create_ai_client")
    @patch("routers.proofread.build_prompts")
    @patch("routers.proofread.get_model_config")
    def test_large_rewrite_with_null_summary(
        self, mock_config, mock_build, mock_create, mock_parse, mock_diffs, client,
    ):
        mock_config.return_value = MOCK_MODEL_CONFIG
        mock_build.return_value = ("s", "u")
        mock_create.return_value = AsyncMock()
        mock_parse.return_value = ParseResult(
            corrected_text="text", summary=None,
            corrections=[], status=ProofreadStatus.SUCCESS, status_reason=None,
        )
        mock_diffs.return_value = DiffResult(
            diffs=[], warnings=["large_rewrite"],
            status=ProofreadStatus.SUCCESS, status_reason=None, corrections=[],
        )

        resp = client.post("/api/proofread", json=VALID_REQUEST, headers=AUTH_HEADERS)
        data = resp.json()
        assert data["summary"] == LARGE_REWRITE_SUMMARY
```

- [ ] **Step 8: Run test to verify it passes**

Run: `cd backend && pytest tests/test_proofread.py::TestSuccessPath -v`
Expected: All 3 tests PASS

- [ ] **Step 9: Run all proofread tests to verify nothing broke**

Run: `cd backend && pytest tests/test_proofread.py -v`
Expected: All 9 tests PASS (6 from Task 1 + 3 from Task 2)

- [ ] **Step 10: Commit**

```bash
git add backend/routers/proofread.py backend/tests/test_proofread.py
git commit -m "feat(backend): implement proofread pipeline with success path

- Orchestrate AI client → prompt builder → response parser → diff service
- Handle large_rewrite warning by appending to summary
- Add 3 success path tests with mocked services"
```

---

## Task 3: AI Error Handling

**Files:**
- Modify: `backend/tests/test_proofread.py`

- [ ] **Step 1: Write failing tests for AI errors**

Add to `backend/tests/test_proofread.py`:

```python
from services.ai_client import AIClientError


class TestAIErrorHandling:
    @patch("routers.proofread.create_ai_client")
    @patch("routers.proofread.build_prompts")
    @patch("routers.proofread.get_model_config")
    def test_ai_timeout_returns_504(self, mock_config, mock_build, mock_create, client):
        mock_config.return_value = MOCK_MODEL_CONFIG
        mock_build.return_value = ("s", "u")
        mock_ai = AsyncMock()
        mock_ai.complete.side_effect = AIClientError("ai_timeout", "タイムアウト")
        mock_create.return_value = mock_ai

        resp = client.post("/api/proofread", json=VALID_REQUEST, headers=AUTH_HEADERS)
        assert resp.status_code == 504
        data = resp.json()
        assert data["error"] == "ai_timeout"
        assert data["request_id"] == "test-req-001"
        assert "タイムアウト" in data["message"]

    @patch("routers.proofread.create_ai_client")
    @patch("routers.proofread.build_prompts")
    @patch("routers.proofread.get_model_config")
    def test_ai_rate_limit_returns_502(self, mock_config, mock_build, mock_create, client):
        mock_config.return_value = MOCK_MODEL_CONFIG
        mock_build.return_value = ("s", "u")
        mock_ai = AsyncMock()
        mock_ai.complete.side_effect = AIClientError("ai_rate_limit", "レート制限")
        mock_create.return_value = mock_ai

        resp = client.post("/api/proofread", json=VALID_REQUEST, headers=AUTH_HEADERS)
        assert resp.status_code == 502
        assert resp.json()["error"] == "ai_rate_limit"

    @patch("routers.proofread.create_ai_client")
    @patch("routers.proofread.build_prompts")
    @patch("routers.proofread.get_model_config")
    def test_ai_invalid_response_returns_502(self, mock_config, mock_build, mock_create, client):
        mock_config.return_value = MOCK_MODEL_CONFIG
        mock_build.return_value = ("s", "u")
        mock_ai = AsyncMock()
        mock_ai.complete.side_effect = AIClientError("ai_invalid_response", "APIエラー")
        mock_create.return_value = mock_ai

        resp = client.post("/api/proofread", json=VALID_REQUEST, headers=AUTH_HEADERS)
        assert resp.status_code == 502
        assert resp.json()["error"] == "ai_invalid_response"

    @patch("routers.proofread.create_ai_client")
    @patch("routers.proofread.build_prompts")
    @patch("routers.proofread.get_model_config")
    def test_unknown_ai_error_code_returns_502(self, mock_config, mock_build, mock_create, client):
        """未知の AI エラーコードはデフォルトで 502 を返す"""
        mock_config.return_value = MOCK_MODEL_CONFIG
        mock_build.return_value = ("s", "u")
        mock_ai = AsyncMock()
        mock_ai.complete.side_effect = AIClientError("unknown_code", "不明なエラー")
        mock_create.return_value = mock_ai

        resp = client.post("/api/proofread", json=VALID_REQUEST, headers=AUTH_HEADERS)
        assert resp.status_code == 502
        data = resp.json()
        # Unknown error codes are sanitized to "ai_invalid_response"
        assert data["error"] == "ai_invalid_response"
```

- [ ] **Step 2: Run tests to verify they pass (error handling already implemented in Task 2 Step 3)**

Run: `cd backend && pytest tests/test_proofread.py::TestAIErrorHandling -v`
Expected: All 4 tests PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_proofread.py
git commit -m "test(backend): add AI error handling tests for proofread route

- Test ai_timeout → 504, ai_rate_limit → 502, ai_invalid_response → 502
- Test unknown error code defaults to 502"
```

---

## Task 4: Parse/Diff Errors + Internal Error

**Files:**
- Modify: `backend/tests/test_proofread.py`

- [ ] **Step 1: Write failing tests for parse error, partial parse, diff timeout, internal error**

Add to `backend/tests/test_proofread.py`:

```python
from schemas import StatusReason


class TestParseAndDiffErrors:
    @patch("routers.proofread.parse_ai_response", new_callable=AsyncMock)
    @patch("routers.proofread.create_ai_client")
    @patch("routers.proofread.build_prompts")
    @patch("routers.proofread.get_model_config")
    def test_parse_error_returns_502(
        self, mock_config, mock_build, mock_create, mock_parse, client,
    ):
        mock_config.return_value = MOCK_MODEL_CONFIG
        mock_build.return_value = ("s", "u")
        mock_create.return_value = AsyncMock()
        mock_parse.return_value = ParseResult(
            corrected_text="", summary=None, corrections=[],
            status=ProofreadStatus.ERROR, status_reason=StatusReason.PARSE_FALLBACK,
        )

        resp = client.post("/api/proofread", json=VALID_REQUEST, headers=AUTH_HEADERS)
        assert resp.status_code == 502
        data = resp.json()
        assert data["error"] == "ai_parse_error"
        assert data["request_id"] == "test-req-001"

    @patch("routers.proofread.parse_ai_response", new_callable=AsyncMock)
    @patch("routers.proofread.create_ai_client")
    @patch("routers.proofread.build_prompts")
    @patch("routers.proofread.get_model_config")
    def test_parse_partial_returns_200_with_partial_status(
        self, mock_config, mock_build, mock_create, mock_parse, client,
    ):
        mock_config.return_value = MOCK_MODEL_CONFIG
        mock_build.return_value = ("s", "u")
        mock_create.return_value = AsyncMock()
        mock_parse.return_value = ParseResult(
            corrected_text="フォールバック抽出テキスト",
            summary=None, corrections=[],
            status=ProofreadStatus.PARTIAL, status_reason=StatusReason.PARSE_FALLBACK,
        )

        resp = client.post("/api/proofread", json=VALID_REQUEST, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "partial"
        assert data["status_reason"] == "parse_fallback"
        assert data["corrected_text"] == "フォールバック抽出テキスト"
        assert data["diffs"] == []
        assert data["warnings"] == []

    @patch("routers.proofread.compute_diffs")
    @patch("routers.proofread.parse_ai_response", new_callable=AsyncMock)
    @patch("routers.proofread.create_ai_client")
    @patch("routers.proofread.build_prompts")
    @patch("routers.proofread.get_model_config")
    def test_diff_timeout_returns_200_with_partial_status(
        self, mock_config, mock_build, mock_create, mock_parse, mock_diffs, client,
    ):
        mock_config.return_value = MOCK_MODEL_CONFIG
        mock_build.return_value = ("s", "u")
        mock_create.return_value = AsyncMock()
        mock_parse.return_value = ParseResult(
            corrected_text="校正済みテキスト", summary="2件の修正",
            corrections=[], status=ProofreadStatus.SUCCESS, status_reason=None,
        )
        mock_diffs.return_value = DiffResult(
            diffs=[], warnings=[],
            status=ProofreadStatus.PARTIAL, status_reason=StatusReason.DIFF_TIMEOUT,
            corrections=[],
        )

        resp = client.post("/api/proofread", json=VALID_REQUEST, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "partial"
        assert data["status_reason"] == "diff_timeout"
        assert data["corrected_text"] == "校正済みテキスト"
        assert data["summary"] == "2件の修正"

    @patch("routers.proofread.build_prompts")
    @patch("routers.proofread.get_model_config")
    def test_internal_error_returns_500(self, mock_config, mock_build, client):
        mock_config.return_value = MOCK_MODEL_CONFIG
        mock_build.side_effect = RuntimeError("unexpected crash")

        resp = client.post("/api/proofread", json=VALID_REQUEST, headers=AUTH_HEADERS)
        assert resp.status_code == 500
        data = resp.json()
        assert data["error"] == "internal_error"
        assert data["request_id"] == "test-req-001"
        assert "内部エラー" in data["message"]
```

- [ ] **Step 2: Run tests to verify they pass (all error handling already implemented)**

Run: `cd backend && pytest tests/test_proofread.py::TestParseAndDiffErrors -v`
Expected: All 4 tests PASS

- [ ] **Step 3: Run all proofread tests**

Run: `cd backend && pytest tests/test_proofread.py -v`
Expected: All 16 tests PASS (6 auth/validation + 3 success + 4 AI errors + 4 parse/diff/internal)

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_proofread.py
git commit -m "test(backend): add parse, diff, and internal error tests for proofread route

- Parse ERROR → 502, parse PARTIAL → 200 with partial status
- Diff timeout → 200 with partial/diff_timeout
- Internal error → 500 with internal_error code"
```

---

## Task 5: Full Test Suite Verification

- [ ] **Step 1: Run complete test suite**

Run: `cd backend && pytest -v`
Expected: All tests pass (existing tests + 16 new proofread tests). No regressions.

- [ ] **Step 2: Run with -x flag to catch first failure**

Run: `cd backend && pytest -x -v`
Expected: All tests pass.

- [ ] **Step 3: Verify test count**

Run: `cd backend && pytest --co -q | tail -1`
Expected: Should show total test count (existing ~100+ tests + 16 new = ~116+ tests)

- [ ] **Step 4: Final commit if any fixes were needed**

Only if Step 1-2 revealed issues. Otherwise, no commit needed for this task.
