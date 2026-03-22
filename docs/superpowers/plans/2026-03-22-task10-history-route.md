# Task 10: History Route — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the History CRUD API with full-text search (FTS5 ngram + LIKE fallback), auto-cleanup (count/capacity limits), and 100KB result JSON truncation.

**Architecture:** A service layer (`history_service.py`) handles all business logic (CRUD, search, truncation, auto-cleanup). The router (`routers/history.py`) is a thin HTTP adapter. FTS5 virtual table + sync triggers are created programmatically via `init_fts5()` in `database.py` at app startup. Search falls back to LIKE when FTS5 ngram is unavailable.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy ORM, SQLite FTS5 (ngram tokenizer), Pydantic v2, pytest

**Design Spec Reference:** §5.1 (endpoints), §5.4 (search/filter), §7 (history management), §9.2 (logging)

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/schemas.py` | Modify | Add 5 history-related Pydantic schemas |
| `backend/database.py` | Modify | Add `init_fts5(engine)` for FTS5 virtual table + triggers |
| `backend/services/history_service.py` | Create | All history business logic (CRUD, search, truncation, auto-cleanup) |
| `backend/routers/history.py` | Create | 6 HTTP endpoints (GET/POST/PATCH/DELETE) |
| `backend/main.py` | Modify | Register history router + call `init_fts5()` at startup |
| `backend/tests/test_history.py` | Create | Comprehensive tests (service + router) |

---

## Task 1: History Pydantic Schemas

**Files:**
- Modify: `backend/schemas.py:101-103` (append after `SettingsUpdateRequest`)
- Test: `backend/tests/test_history.py`

- [ ] **Step 1: Write the failing schema tests**

```python
# backend/tests/test_history.py
"""Tests for History CRUD API (§5.1, §5.4, §7)."""
import pytest
from pydantic import ValidationError


class TestHistorySchemas:
    """Schema validation tests."""

    def test_create_request_valid(self):
        from schemas import HistoryCreateRequest, ProofreadResponse
        req = HistoryCreateRequest(
            input_text="テスト文書",
            result=ProofreadResponse(
                request_id="req-1",
                status="success",
                corrected_text="校正済み",
            ),
            model="kimi-k2.5",
            document_type="email",
        )
        assert req.input_text == "テスト文書"

    def test_create_request_requires_input_text(self):
        from schemas import HistoryCreateRequest, ProofreadResponse
        with pytest.raises(ValidationError):
            HistoryCreateRequest(
                input_text="",
                result=ProofreadResponse(
                    request_id="req-1", status="success", corrected_text="x",
                ),
                model="kimi-k2.5",
                document_type="email",
            )

    def test_create_request_input_text_max_8000(self):
        from schemas import HistoryCreateRequest, ProofreadResponse
        with pytest.raises(ValidationError):
            HistoryCreateRequest(
                input_text="あ" * 8001,
                result=ProofreadResponse(
                    request_id="req-1", status="success", corrected_text="x",
                ),
                model="kimi-k2.5",
                document_type="email",
            )

    def test_create_request_memo_optional(self):
        from schemas import HistoryCreateRequest, ProofreadResponse
        req = HistoryCreateRequest(
            input_text="テスト",
            result=ProofreadResponse(
                request_id="req-1", status="success", corrected_text="校正済み",
            ),
            model="kimi-k2.5",
            document_type="email",
        )
        assert req.memo is None

    def test_update_request_memo_only(self):
        from schemas import HistoryUpdateRequest
        req = HistoryUpdateRequest(memo="メモ更新")
        assert req.memo == "メモ更新"

    def test_update_request_memo_nullable(self):
        from schemas import HistoryUpdateRequest
        req = HistoryUpdateRequest(memo=None)
        assert req.memo is None

    def test_list_item_preview_truncated_to_50(self):
        from schemas import HistoryListItemResponse
        from datetime import datetime, timezone
        item = HistoryListItemResponse(
            id=1,
            preview="あ" * 100,
            document_type="email",
            model="kimi-k2.5",
            created_at=datetime.now(timezone.utc),
            truncated=False,
            memo=None,
        )
        assert len(item.preview) == 50

    def test_detail_response_contains_result(self):
        from schemas import HistoryDetailResponse, ProofreadResponse
        from datetime import datetime, timezone
        detail = HistoryDetailResponse(
            id=1,
            input_text="テスト",
            result=ProofreadResponse(
                request_id="req-1", status="success", corrected_text="校正済み",
            ),
            model="kimi-k2.5",
            document_type="email",
            created_at=datetime.now(timezone.utc),
            truncated=False,
            memo=None,
        )
        assert detail.result.corrected_text == "校正済み"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_history.py::TestHistorySchemas -v`
Expected: FAIL — `ImportError: cannot import name 'HistoryCreateRequest'`

- [ ] **Step 3: Implement schemas**

Append to `backend/schemas.py`:

```python
# === History schemas (§5.1, §7) ===


class HistoryCreateRequest(BaseModel):
    input_text: str = Field(min_length=1, max_length=8000)
    result: ProofreadResponse
    model: str = Field(min_length=1, max_length=50)
    document_type: str = Field(min_length=1, max_length=20)
    memo: str | None = None


class HistoryUpdateRequest(BaseModel):
    memo: str | None = None


class HistoryListItemResponse(BaseModel):
    id: int
    preview: str
    document_type: str
    model: str
    created_at: datetime
    truncated: bool
    memo: str | None = None


class HistoryDetailResponse(BaseModel):
    id: int
    input_text: str
    result: ProofreadResponse
    model: str
    document_type: str
    created_at: datetime
    truncated: bool
    memo: str | None = None


class HistoryListResponse(BaseModel):
    items: list[HistoryListItemResponse]
    total: int
```

**Note:** `datetime` import is needed at the top of `schemas.py`. Check if it's already imported. If not, add `from datetime import datetime`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_history.py::TestHistorySchemas -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/schemas.py backend/tests/test_history.py
git commit -m "feat(backend): add history Pydantic schemas with validation"
```

---

## Task 2: FTS5 Table Setup

**Files:**
- Modify: `backend/database.py:91` (append after `check_fts5_ngram_support`)
- Test: `backend/tests/test_history.py`

- [ ] **Step 1: Write the failing FTS5 init test**

Append to `backend/tests/test_history.py`:

```python
class TestFts5Setup:
    """FTS5 virtual table creation tests."""

    def test_init_fts5_creates_fts_table_when_supported(self, db_engine):
        from database import init_fts5, FTS5_NGRAM_SUPPORTED
        if not FTS5_NGRAM_SUPPORTED:
            pytest.skip("FTS5 ngram not supported in this environment")
        from sqlalchemy import text
        init_fts5(db_engine)
        with db_engine.connect() as conn:
            result = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='history_fts'")
            )
            assert result.fetchone() is not None

    def test_init_fts5_is_idempotent(self, db_engine):
        from database import init_fts5, FTS5_NGRAM_SUPPORTED
        if not FTS5_NGRAM_SUPPORTED:
            pytest.skip("FTS5 ngram not supported in this environment")
        from sqlalchemy import text
        init_fts5(db_engine)
        init_fts5(db_engine)  # 二回呼び出してもエラーにならない
        with db_engine.connect() as conn:
            result = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='history_fts'")
            )
            assert result.fetchone() is not None

    def test_init_fts5_creates_triggers_when_supported(self, db_engine):
        from database import init_fts5, FTS5_NGRAM_SUPPORTED
        if not FTS5_NGRAM_SUPPORTED:
            pytest.skip("FTS5 ngram not supported in this environment")
        from sqlalchemy import text
        init_fts5(db_engine)
        with db_engine.connect() as conn:
            result = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='trigger' AND name='history_ai'")
            )
            assert result.fetchone() is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_history.py::TestFts5Setup -v`
Expected: FAIL — `ImportError: cannot import name 'init_fts5'`

- [ ] **Step 3: Implement `init_fts5()`**

Append to `backend/database.py`:

```python
def init_fts5(engine) -> None:
    """Create FTS5 virtual table and sync triggers for history full-text search.

    Uses IF NOT EXISTS so it's safe to call multiple times.
    Only creates the table if FTS5 ngram tokenizer is supported.
    """
    if not check_fts5_ngram_support():
        return

    from sqlalchemy import text

    with engine.connect() as conn:
        conn.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS history_fts
            USING fts5(input_text, memo, content=history, tokenize='ngram')
        """))
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS history_ai AFTER INSERT ON history BEGIN
                INSERT INTO history_fts(rowid, input_text, memo)
                VALUES (new.id, new.input_text, COALESCE(new.memo, ''));
            END
        """))
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS history_ad AFTER DELETE ON history BEGIN
                INSERT INTO history_fts(history_fts, rowid, input_text, memo)
                VALUES ('delete', old.id, old.input_text, COALESCE(old.memo, ''));
            END
        """))
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS history_au AFTER UPDATE ON history BEGIN
                INSERT INTO history_fts(history_fts, rowid, input_text, memo)
                VALUES ('delete', old.id, old.input_text, COALESCE(old.memo, ''));
                INSERT INTO history_fts(rowid, input_text, memo)
                VALUES (new.id, new.input_text, COALESCE(new.memo, ''));
            END
        """))
        conn.commit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_history.py::TestFts5Setup -v`
Expected: All PASS (or SKIP if FTS5 ngram not available)

- [ ] **Step 5: Update main.py to call `init_fts5()` at startup**

In `backend/main.py`, after the existing `init_db()` call (line 153), add:

```python
# FTS5 テーブル初期化（履歴全文検索用）
from database import init_fts5
init_fts5(_engine)
```

Also add `_engine` import — it's defined at module level in `database.py`. Update the existing import on line 10:

```python
from database import init_db, check_fts5_ngram_support, init_fts5, _engine
```

Then replace the standalone `init_db()` and FTS5 check block (lines 150-161) with:

```python
app = create_app()

# DB 初期化（テーブルが存在しない場合は作成）
init_db()

# FTS5 テーブル初期化（履歴全文検索用）
init_fts5(_engine)

setup_logging()

# FTS5 ngram トークナイザ対応状況をログ出力
if check_fts5_ngram_support():
    logger.info("FTS5 ngram tokenizer: supported")
else:
    logger.warning("FTS5 ngram tokenizer: NOT supported. Unicode61 will be used as fallback.")
```

- [ ] **Step 6: Run all existing tests to verify no regression**

Run: `cd backend && pytest -v`
Expected: All existing tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/database.py backend/main.py backend/tests/test_history.py
git commit -m "feat(backend): add FTS5 virtual table setup for history search"
```

---

## Task 3: History Service — Save with Truncation

**Files:**
- Create: `backend/services/history_service.py`
- Test: `backend/tests/test_history.py`

- [ ] **Step 1: Write the failing save tests**

Append to `backend/tests/test_history.py`:

```python
@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-secret-token"}


@pytest.fixture
def client(app_client):
    return app_client


def _make_proofread_response(**overrides):
    """Helper to build a ProofreadResponse dict for testing."""
    from schemas import ProofreadResponse
    defaults = dict(
        request_id="test-req-1",
        status="success",
        corrected_text="校正済みテキスト",
        summary="3件の修正を行いました。",
    )
    defaults.update(overrides)
    return ProofreadResponse(**defaults)


def _create_history_via_service(db_session, **overrides):
    """Helper to create a history record via the service layer."""
    from services.history_service import create_history
    defaults = dict(
        db=db_session,
        input_text="テスト入力文書です。",
        result=_make_proofread_response(),
        model="kimi-k2.5",
        document_type="email",
        memo=None,
    )
    defaults.update(overrides)
    return create_history(**defaults)


class TestCreateHistory:
    """History service — save tests."""

    def test_saves_to_db(self, db_session):
        from services.history_service import create_history, get_history_by_id
        record = _create_history_via_service(db_session)
        fetched = get_history_by_id(db_session, record.id)
        assert fetched is not None
        assert fetched.input_text == "テスト入力文書です。"

    def test_returns_saved_record(self, db_session):
        from services.history_service import create_history
        record = _create_history_via_service(db_session)
        assert record.id is not None
        assert record.model == "kimi-k2.5"

    def test_stores_result_json_as_string(self, db_session):
        from services.history_service import create_history, get_history_by_id
        import json
        record = _create_history_via_service(db_session)
        fetched = get_history_by_id(db_session, record.id)
        parsed = json.loads(fetched.result_json)
        assert parsed["corrected_text"] == "校正済みテキスト"

    def test_truncates_result_json_over_100kb(self, db_session):
        from services.history_service import create_history, get_history_by_id
        import json
        # 100KB を超える corrections を生成
        big_corrections = [
            {
                "original": f"修正前テキスト{i:04d}です",
                "corrected": f"修正後テキスト{i:04d}です",
                "reason": f"理由{i}",
                "category": "誤字脱字",
                "diff_matched": True,
            }
            for i in range(3000)
        ]
        big_result = _make_proofread_response(corrections=big_corrections)
        record = _create_history_via_service(db_session, result=big_result)
        fetched = get_history_by_id(db_session, record.id)
        assert fetched.truncated is True
        parsed = json.loads(fetched.result_json)
        assert len(parsed.get("corrections", [])) == 0
        assert parsed["summary"] == "3件の修正を行いました。"
        assert parsed["corrected_text"] == "校正済みテキスト"

    def test_no_truncation_under_100kb(self, db_session):
        from services.history_service import create_history
        result = _make_proofread_response()
        record = _create_history_via_service(db_session, result=result)
        assert record.truncated is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_history.py::TestCreateHistory -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'services.history_service'`

- [ ] **Step 3: Implement `history_service.py` — save + truncation**

Create `backend/services/history_service.py`:

```python
"""History CRUD service (§5.1, §5.4, §7)."""
import json
import logging
import os

from sqlalchemy import or_, text
from sqlalchemy.orm import Session

from database import FTS5_NGRAM_SUPPORTED, get_database_url
from models import History

logger = logging.getLogger("govassist")

RESULT_JSON_MAX_BYTES = 100 * 1024  # 100KB (§7.1)
CAPACITY_LIMIT_BYTES = 20 * 1024 * 1024  # 20MB (§7.1)
DEFAULT_HISTORY_LIMIT = 50


def _truncate_result_json(result) -> tuple[str, bool]:
    """Serialize result to JSON, truncate if > 100KB.

    Returns (json_string, truncated_flag).
    Truncation: keep corrected_text + summary, remove corrections/diffs.
    """
    json_str = result.model_dump_json()
    if len(json_str.encode("utf-8")) <= RESULT_JSON_MAX_BYTES:
        return json_str, False

    logger.info("Result JSON exceeds 100KB, truncating corrections/diffs")
    truncated = result.model_copy(update={
        "corrections": [],
        "diffs": [],
    })
    return truncated.model_dump_json(), True


def _get_history_limit(db: Session) -> int:
    """Read history_limit from settings table."""
    from models import Settings
    row = db.query(Settings).filter_by(key="history_limit").first()
    if row:
        try:
            return int(row.value)
        except (ValueError, TypeError):
            pass
    return DEFAULT_HISTORY_LIMIT


def _get_db_file_size() -> int | None:
    """Get database file size in bytes. Returns None for in-memory DBs."""
    url = get_database_url()
    if ":memory:" in url:
        return None
    db_path = url.replace("sqlite:///", "")
    if not os.path.exists(db_path):
        return 0
    return os.path.getsize(db_path)


def _enforce_count_limit(db: Session) -> None:
    """Delete oldest records exceeding the configured count limit."""
    limit = _get_history_limit(db)
    count = db.query(History).count()
    if count <= limit:
        return

    excess = count - limit
    oldest_ids = (
        db.query(History.id)
        .order_by(History.created_at.asc())
        .limit(excess)
        .all()
    )
    if oldest_ids:
        ids_to_delete = [row[0] for row in oldest_ids]
        db.query(History).filter(History.id.in_(ids_to_delete)).delete(synchronize_session="fetch")
        db.flush()
        logger.info("Auto-deleted %d oldest history records (count limit: %d)", len(ids_to_delete), limit)


def _enforce_capacity_limit(db: Session) -> None:
    """Delete oldest records if DB file exceeds 20MB."""
    size = _get_db_file_size()
    if size is None or size <= CAPACITY_LIMIT_BYTES:
        return

    logger.warning(
        "DB size %.1fMB exceeds 20MB limit, auto-deleting oldest records",
        size / (1024 * 1024),
    )
    while _get_db_file_size() and _get_db_file_size() > CAPACITY_LIMIT_BYTES:
        oldest = db.query(History).order_by(History.created_at.asc()).first()
        if oldest is None:
            break
        db.delete(oldest)
        db.flush()


def create_history(
    db: Session,
    *,
    input_text: str,
    result,
    model: str,
    document_type: str,
    memo: str | None = None,
) -> History:
    """Save a proofread result to history. Enforces truncation and auto-cleanup."""
    result_json, truncated = _truncate_result_json(result)

    record = History(
        input_text=input_text,
        result_json=result_json,
        model=model,
        document_type=document_type,
        memo=memo,
        truncated=truncated,
    )
    db.add(record)
    db.flush()

    _enforce_count_limit(db)
    _enforce_capacity_limit(db)

    return record
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_history.py::TestCreateHistory -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/history_service.py backend/tests/test_history.py
git commit -m "feat(backend): implement history save with 100KB truncation"
```

---

## Task 4: History Service — List, Get, Update, Delete

**Files:**
- Modify: `backend/services/history_service.py`
- Test: `backend/tests/test_history.py`

- [ ] **Step 1: Write the failing tests for list, get, update, delete**

Append to `backend/tests/test_history.py`:

```python
class TestGetHistoryList:
    """History service — list tests."""

    def test_returns_items_in_descending_order(self, db_session):
        from services.history_service import get_history_list
        for i in range(3):
            _create_history_via_service(db_session, input_text=f"文書{i}")
        items, total = get_history_list(db_session)
        assert total == 3
        assert items[0].input_text == "文書2"

    def test_respects_limit(self, db_session):
        from services.history_service import get_history_list
        for i in range(5):
            _create_history_via_service(db_session, input_text=f"文書{i}")
        items, total = get_history_list(db_session, limit=2)
        assert total == 5
        assert len(items) == 2

    def test_respects_offset(self, db_session):
        from services.history_service import get_history_list
        for i in range(5):
            _create_history_via_service(db_session, input_text=f"文書{i}")
        items, total = get_history_list(db_session, limit=2, offset=2)
        assert len(items) == 2
        # offset=2 skips the 2 newest, so we get items[2] and items[3]
        assert items[0].input_text == "文書2"

    def test_filter_by_document_type(self, db_session):
        from services.history_service import get_history_list
        _create_history_via_service(db_session, document_type="email")
        _create_history_via_service(db_session, document_type="official")
        _create_history_via_service(db_session, document_type="email")
        items, total = get_history_list(db_session, document_type="email")
        assert total == 2
        assert all(it.document_type == "email" for it in items)

    def test_filter_by_date_range(self, db_session):
        from services.history_service import get_history_list
        from datetime import datetime, timezone, timedelta
        # Create records with specific timestamps
        h1 = _create_history_via_service(db_session)
        h1.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        h2 = _create_history_via_service(db_session)
        h2.created_at = datetime(2026, 3, 1, tzinfo=timezone.utc)
        h3 = _create_history_via_service(db_session)
        h3.created_at = datetime(2026, 6, 1, tzinfo=timezone.utc)
        db_session.flush()
        items, total = get_history_list(
            db_session,
            date_from=datetime(2026, 2, 1, tzinfo=timezone.utc),
            date_to=datetime(2026, 5, 1, tzinfo=timezone.utc),
        )
        assert total == 1

    def test_empty_list(self, db_session):
        from services.history_service import get_history_list
        items, total = get_history_list(db_session)
        assert total == 0
        assert items == []

    def test_default_limit_is_20(self, db_session):
        from services.history_service import get_history_list
        for i in range(25):
            _create_history_via_service(db_session, input_text=f"文書{i}")
        items, total = get_history_list(db_session)
        assert len(items) == 20
        assert total == 25


class TestGetHistoryById:
    """History service — get by id tests."""

    def test_returns_record(self, db_session):
        from services.history_service import get_history_by_id
        record = _create_history_via_service(db_session, input_text="特定文書")
        fetched = get_history_by_id(db_session, record.id)
        assert fetched is not None
        assert fetched.input_text == "特定文書"

    def test_returns_none_for_nonexistent(self, db_session):
        from services.history_service import get_history_by_id
        result = get_history_by_id(db_session, 9999)
        assert result is None


class TestUpdateHistoryMemo:
    """History service — update memo tests."""

    def test_updates_memo(self, db_session):
        from services.history_service import update_history_memo, get_history_by_id
        record = _create_history_via_service(db_session)
        updated = update_history_memo(db_session, record.id, "新しいメモ")
        assert updated.memo == "新しいメモ"
        fetched = get_history_by_id(db_session, record.id)
        assert fetched.memo == "新しいメモ"

    def test_clears_memo_with_none(self, db_session):
        from services.history_service import update_history_memo, get_history_by_id
        record = _create_history_via_service(db_session, memo="元のメモ")
        updated = update_history_memo(db_session, record.id, None)
        assert updated.memo is None

    def test_returns_none_for_nonexistent(self, db_session):
        from services.history_service import update_history_memo
        result = update_history_memo(db_session, 9999, "メモ")
        assert result is None


class TestDeleteHistory:
    """History service — delete tests."""

    def test_delete_single(self, db_session):
        from services.history_service import delete_history, get_history_by_id
        record = _create_history_via_service(db_session)
        delete_history(db_session, record.id)
        assert get_history_by_id(db_session, record.id) is None

    def test_delete_nonexistent_returns_false(self, db_session):
        from services.history_service import delete_history
        assert delete_history(db_session, 9999) is False

    def test_delete_all(self, db_session):
        from services.history_service import delete_all_history, get_history_list
        for i in range(5):
            _create_history_via_service(db_session)
        count = delete_all_history(db_session)
        assert count == 5
        items, total = get_history_list(db_session)
        assert total == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_history.py::TestGetHistoryList tests/test_history.py::TestGetHistoryById tests/test_history.py::TestUpdateHistoryMemo tests/test_history.py::TestDeleteHistory -v`
Expected: FAIL — `ImportError` for missing functions

- [ ] **Step 3: Implement list, get, update, delete functions**

Append to `backend/services/history_service.py`:

```python
def get_history_list(
    db: Session,
    *,
    q: str | None = None,
    document_type: str | None = None,
    date_from: "datetime | None" = None,
    date_to: "datetime | None" = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[History], int]:
    """List history records with optional filters and pagination."""
    query = db.query(History)

    # Filters
    if document_type:
        query = query.filter(History.document_type == document_type)
    if date_from:
        query = query.filter(History.created_at >= date_from)
    if date_to:
        query = query.filter(History.created_at <= date_to)

    # Full-text search
    if q:
        query = _apply_search(db, query, q)

    # Count before pagination
    total = query.count()

    # Order by created_at DESC, then paginate
    items = (
        query.order_by(History.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return items, total


def get_history_by_id(db: Session, history_id: int) -> History | None:
    """Get a single history record by ID."""
    return db.query(History).filter(History.id == history_id).first()


def update_history_memo(db: Session, history_id: int, memo: str | None) -> History | None:
    """Update the memo field of a history record."""
    record = get_history_by_id(db, history_id)
    if record is None:
        return None
    record.memo = memo
    db.flush()
    return record


def delete_history(db: Session, history_id: int) -> bool:
    """Delete a single history record. Returns True if deleted."""
    record = get_history_by_id(db, history_id)
    if record is None:
        return False
    db.delete(record)
    db.flush()
    return True


def delete_all_history(db: Session) -> int:
    """Delete all history records. Returns count of deleted records."""
    count = db.query(History).count()
    if count > 0:
        db.query(History).delete()
        db.flush()
    return count


def _apply_search(db: Session, query, q: str):
    """Apply full-text search using FTS5 or LIKE fallback."""
    if FTS5_NGRAM_SUPPORTED:
        try:
            return _search_with_fts5(query, q)
        except Exception:
            logger.warning("FTS5 search failed, falling back to LIKE")
    return _search_with_like(query, q)


def _search_with_fts5(query, q: str):
    """Search using FTS5 ngram virtual table."""
    return (
        query.join(
            text("history_fts"),
            text("history_fts.rowid = history.id"),
        )
        .filter(text("history_fts MATCH :q"))
        .params(q=q)
    )


def _search_with_like(query, q: str):
    """Fallback search using LIKE."""
    pattern = f"%{q}%"
    return query.filter(
        or_(
            History.input_text.like(pattern),
            History.memo.like(pattern),
        )
    )
```

**Note:** The `datetime` type hint in `get_history_list` needs `from datetime import datetime` at the top of the file. Add it.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_history.py::TestGetHistoryList tests/test_history.py::TestGetHistoryById tests/test_history.py::TestUpdateHistoryMemo tests/test_history.py::TestDeleteHistory -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/history_service.py backend/tests/test_history.py
git commit -m "feat(backend): implement history CRUD service (list, get, update, delete)"
```

---

## Task 5: History Service — Auto-cleanup

**Files:**
- Modify: `backend/tests/test_history.py`

- [ ] **Step 1: Write the failing auto-cleanup tests**

Append to `backend/tests/test_history.py`:

```python
class TestAutoCleanup:
    """History service — auto-cleanup tests (§7.1)."""

    def test_count_limit_deletes_oldest(self, db_session):
        from services.history_service import create_history, get_history_list
        from models import Settings
        # Set limit to 3
        db_session.add(Settings(key="history_limit", value="3"))
        db_session.flush()
        # Create 5 records
        records = []
        for i in range(5):
            records.append(_create_history_via_service(db_session, input_text=f"文書{i}"))
        # Only the 3 newest should remain
        items, total = get_history_list(db_session)
        assert total == 3
        # Newest 3: 文書4, 文書3, 文書2
        input_texts = [it.input_text for it in items]
        assert "文書4" in input_texts
        assert "文書3" in input_texts
        assert "文書2" in input_texts
        assert "文書0" not in input_texts
        assert "文書1" not in input_texts

    def test_default_count_limit_is_50(self, db_session):
        """デフォルトの保存件数上限は 50 件"""
        from services.history_service import _get_history_limit
        assert _get_history_limit(db_session) == 50

    def test_count_limit_reads_from_settings(self, db_session):
        from services.history_service import _get_history_limit
        from models import Settings
        db_session.add(Settings(key="history_limit", value="10"))
        db_session.flush()
        assert _get_history_limit(db_session) == 10

    def test_count_limit_handles_invalid_setting(self, db_session):
        from services.history_service import _get_history_limit
        from models import Settings
        db_session.add(Settings(key="history_limit", value="not-a-number"))
        db_session.flush()
        assert _get_history_limit(db_session) == 50
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_history.py::TestAutoCleanup -v`
Expected: FAIL — The count limit enforcement in `_enforce_count_limit` is already implemented in Task 3, but the test may reveal bugs in the implementation.

Run and fix any failures.

- [ ] **Step 3: Verify all pass**

Run: `cd backend && pytest tests/test_history.py::TestAutoCleanup -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_history.py
git commit -m "test(backend): add auto-cleanup tests for history count limit"
```

---

## Task 6: History Service — Search

**Files:**
- Modify: `backend/tests/test_history.py`

- [ ] **Step 1: Write the failing search tests**

Append to `backend/tests/test_history.py`:

```python
class TestSearchHistory:
    """History service — search tests (§5.4)."""

    def test_like_search_matches_input_text(self, db_session):
        from services.history_service import get_history_list
        _create_history_via_service(db_session, input_text="申請書を提出してください")
        _create_history_via_service(db_session, input_text="会議の議事録です")
        items, total = get_history_list(db_session, q="申請書")
        assert total == 1
        assert "申請書" in items[0].input_text

    def test_like_search_matches_memo(self, db_session):
        from services.history_service import get_history_list
        _create_history_via_service(db_session, input_text="テスト1", memo="重要な文書")
        _create_history_via_service(db_session, input_text="テスト2", memo="普通の文書")
        items, total = get_history_list(db_session, q="重要")
        assert total == 1
        assert items[0].memo == "重要な文書"

    def test_like_search_matches_both(self, db_session):
        from services.history_service import get_history_list
        _create_history_via_service(db_session, input_text="申請書です", memo="申請に関するメモ")
        _create_history_via_service(db_session, input_text="別の文書", memo=" unrelated")
        items, total = get_history_list(db_session, q="申請")
        assert total == 2

    def test_like_search_no_match(self, db_session):
        from services.history_service import get_history_list
        _create_history_via_service(db_session, input_text="テスト文書")
        items, total = get_history_list(db_session, q="存在しないキーワード")
        assert total == 0

    def test_search_combined_with_document_type_filter(self, db_session):
        from services.history_service import get_history_list
        _create_history_via_service(db_session, input_text="申請書です", document_type="email")
        _create_history_via_service(db_session, input_text="申請書の写し", document_type="official")
        items, total = get_history_list(db_session, q="申請書", document_type="email")
        assert total == 1

    def test_empty_query_returns_all(self, db_session):
        from services.history_service import get_history_list
        _create_history_via_service(db_session, input_text="文書1")
        _create_history_via_service(db_session, input_text="文書2")
        items, total = get_history_list(db_session, q="")
        assert total == 2

    def test_none_query_returns_all(self, db_session):
        from services.history_service import get_history_list
        _create_history_via_service(db_session, input_text="文書1")
        items, total = get_history_list(db_session, q=None)
        assert total == 1
```

- [ ] **Step 2: Run test to verify it passes (search already implemented in Task 4)**

Run: `cd backend && pytest tests/test_history.py::TestSearchHistory -v`
Expected: All PASS — search was implemented as part of Task 4

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_history.py
git commit -m "test(backend): add history search tests (LIKE fallback)"
```

---

## Task 7: History Router + App Registration

**Files:**
- Create: `backend/routers/history.py`
- Modify: `backend/main.py:144-145` (register router)
- Test: `backend/tests/test_history.py`

- [ ] **Step 1: Write the failing router tests**

Append to `backend/tests/test_history.py`:

```python
class TestGetHistoryRouter:
    """GET /api/history endpoint tests."""

    def test_returns_200_with_auth(self, client, auth_headers):
        resp = client.get("/api/history", headers=auth_headers)
        assert resp.status_code == 200

    def test_returns_401_without_auth(self, client):
        resp = client.get("/api/history")
        assert resp.status_code == 401

    def test_returns_empty_list(self, client, auth_headers):
        resp = client.get("/api/history", headers=auth_headers)
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_returns_items_with_preview(self, client, auth_headers, db_session):
        _create_history_via_service(db_session, input_text="あ" * 100)
        resp = client.get("/api/history", headers=auth_headers)
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"][0]["preview"]) == 50

    def test_query_param_q_filters(self, client, auth_headers, db_session):
        _create_history_via_service(db_session, input_text="申請書を提出")
        _create_history_via_service(db_session, input_text="会議の議事録")
        resp = client.get("/api/history?q=申請書", headers=auth_headers)
        data = resp.json()
        assert data["total"] == 1

    def test_query_param_document_type_filters(self, client, auth_headers, db_session):
        _create_history_via_service(db_session, document_type="email")
        _create_history_via_service(db_session, document_type="official")
        resp = client.get("/api/history?document_type=official", headers=auth_headers)
        data = resp.json()
        assert data["total"] == 1

    def test_query_param_limit(self, client, auth_headers, db_session):
        for i in range(5):
            _create_history_via_service(db_session, input_text=f"文書{i}")
        resp = client.get("/api/history?limit=2", headers=auth_headers)
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5

    def test_query_param_offset(self, client, auth_headers, db_session):
        for i in range(5):
            _create_history_via_service(db_session, input_text=f"文書{i}")
        resp = client.get("/api/history?limit=2&offset=3", headers=auth_headers)
        data = resp.json()
        assert len(data["items"]) == 2

    def test_query_param_date_range(self, client, auth_headers, db_session):
        from datetime import datetime, timezone
        h = _create_history_via_service(db_session)
        h.created_at = datetime(2026, 3, 15, tzinfo=timezone.utc)
        db_session.flush()
        resp = client.get(
            "/api/history?date_from=2026-03-01T00:00:00Z&date_to=2026-03-20T00:00:00Z",
            headers=auth_headers,
        )
        data = resp.json()
        assert data["total"] == 1


class TestPostHistoryRouter:
    """POST /api/history endpoint tests."""

    def test_returns_201_with_auth(self, client, auth_headers):
        resp = client.post(
            "/api/history",
            headers=auth_headers,
            json={
                "input_text": "テスト文書です。",
                "result": {
                    "request_id": "req-1",
                    "status": "success",
                    "corrected_text": "校正済みテキストです。",
                    "summary": "1件修正",
                },
                "model": "kimi-k2.5",
                "document_type": "email",
            },
        )
        assert resp.status_code == 201

    def test_returns_401_without_auth(self, client):
        resp = client.post("/api/history", json={"input_text": "test"})
        assert resp.status_code == 401

    def test_returns_created_record(self, client, auth_headers):
        resp = client.post(
            "/api/history",
            headers=auth_headers,
            json={
                "input_text": "テスト",
                "result": {
                    "request_id": "req-1",
                    "status": "success",
                    "corrected_text": "校正済み",
                },
                "model": "kimi-k2.5",
                "document_type": "report",
            },
        )
        data = resp.json()
        assert "id" in data
        assert data["input_text"] == "テスト"
        assert data["document_type"] == "report"

    def test_validates_input_text_min_length(self, client, auth_headers):
        resp = client.post(
            "/api/history",
            headers=auth_headers,
            json={
                "input_text": "",
                "result": {"request_id": "r", "status": "success", "corrected_text": "x"},
                "model": "kimi-k2.5",
                "document_type": "email",
            },
        )
        assert resp.status_code == 422

    def test_validates_input_text_max_length(self, client, auth_headers):
        resp = client.post(
            "/api/history",
            headers=auth_headers,
            json={
                "input_text": "あ" * 8001,
                "result": {"request_id": "r", "status": "success", "corrected_text": "x"},
                "model": "kimi-k2.5",
                "document_type": "email",
            },
        )
        assert resp.status_code == 422

    def test_saves_optional_memo(self, client, auth_headers):
        resp = client.post(
            "/api/history",
            headers=auth_headers,
            json={
                "input_text": "テスト",
                "result": {"request_id": "r", "status": "success", "corrected_text": "校正"},
                "model": "kimi-k2.5",
                "document_type": "email",
                "memo": "メモです",
            },
        )
        data = resp.json()
        assert data["memo"] == "メモです"


class TestGetHistoryByIdRouter:
    """GET /api/history/{id} endpoint tests."""

    def test_returns_200_with_auth(self, client, auth_headers, db_session):
        record = _create_history_via_service(db_session)
        resp = client.get(f"/api/history/{record.id}", headers=auth_headers)
        assert resp.status_code == 200

    def test_returns_404_for_nonexistent(self, client, auth_headers):
        resp = client.get("/api/history/9999", headers=auth_headers)
        assert resp.status_code == 404

    def test_returns_detail_with_result(self, client, auth_headers, db_session):
        record = _create_history_via_service(db_session)
        resp = client.get(f"/api/history/{record.id}", headers=auth_headers)
        data = resp.json()
        assert data["id"] == record.id
        assert data["input_text"] == "テスト入力文書です。"
        assert "result" in data
        assert data["result"]["corrected_text"] == "校正済みテキスト"


class TestPatchHistoryRouter:
    """PATCH /api/history/{id} endpoint tests."""

    def test_updates_memo(self, client, auth_headers, db_session):
        record = _create_history_via_service(db_session)
        resp = client.patch(
            f"/api/history/{record.id}",
            json={"memo": "更新メモ"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["memo"] == "更新メモ"

    def test_clears_memo_with_null(self, client, auth_headers, db_session):
        record = _create_history_via_service(db_session, memo="元メモ")
        resp = client.patch(
            f"/api/history/{record.id}",
            json={"memo": None},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["memo"] is None

    def test_returns_404_for_nonexistent(self, client, auth_headers):
        resp = client.patch("/api/history/9999", json={"memo": "x"}, headers=auth_headers)
        assert resp.status_code == 404

    def test_returns_401_without_auth(self, client, db_session):
        record = _create_history_via_service(db_session)
        resp = client.patch(f"/api/history/{record.id}", json={"memo": "x"})
        assert resp.status_code == 401


class TestDeleteHistoryRouter:
    """DELETE /api/history/{id} and DELETE /api/history endpoint tests."""

    def test_delete_single_returns_200(self, client, auth_headers, db_session):
        record = _create_history_via_service(db_session)
        resp = client.delete(f"/api/history/{record.id}", headers=auth_headers)
        assert resp.status_code == 200

    def test_delete_single_removes_record(self, client, auth_headers, db_session):
        record = _create_history_via_service(db_session)
        client.delete(f"/api/history/{record.id}", headers=auth_headers)
        resp = client.get(f"/api/history/{record.id}", headers=auth_headers)
        assert resp.status_code == 404

    def test_delete_single_404_nonexistent(self, client, auth_headers):
        resp = client.delete("/api/history/9999", headers=auth_headers)
        assert resp.status_code == 404

    def test_delete_all_returns_200(self, client, auth_headers, db_session):
        for i in range(3):
            _create_history_via_service(db_session)
        resp = client.delete("/api/history", headers=auth_headers)
        assert resp.status_code == 200

    def test_delete_all_removes_everything(self, client, auth_headers, db_session):
        for i in range(3):
            _create_history_via_service(db_session)
        client.delete("/api/history", headers=auth_headers)
        resp = client.get("/api/history", headers=auth_headers)
        assert resp.json()["total"] == 0

    def test_delete_returns_401_without_auth(self, client):
        resp = client.delete("/api/history")
        assert resp.status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_history.py -k "Router" -v`
Expected: FAIL — 404 (router not registered)

- [ ] **Step 3: Implement the router**

Create `backend/routers/history.py`:

```python
"""GET/POST/PATCH/DELETE /api/history — 履歴 CRUD (§5.1, §5.4, §7)."""
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from dependencies import verify_token
from schemas import (
    HistoryCreateRequest,
    HistoryDetailResponse,
    HistoryListItemResponse,
    HistoryListResponse,
    HistoryUpdateRequest,
    ProofreadResponse,
)
from services.history_service import (
    create_history,
    delete_all_history,
    delete_history,
    get_history_by_id,
    get_history_list,
    update_history_memo,
)

logger = logging.getLogger("govassist")

router = APIRouter(prefix="/api", tags=["history"])


@router.get("/history", response_model=HistoryListResponse)
async def list_history(
    q: str | None = Query(None, description="キーワード検索"),
    document_type: str | None = Query(None, description="文書種別フィルタ"),
    date_from: datetime | None = Query(None, description="開始日 (ISO 8601)"),
    date_to: datetime | None = Query(None, description="終了日 (ISO 8601)"),
    limit: int = Query(20, ge=1, le=200, description="取得件数"),
    offset: int = Query(0, ge=0, description="オフセット"),
    token: str = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """履歴一覧を取得する (§5.4)."""
    items, total = get_history_list(
        db,
        q=q,
        document_type=document_type,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return HistoryListResponse(
        items=[
            HistoryListItemResponse(
                id=h.id,
                preview=h.input_text[:50],
                document_type=h.document_type,
                model=h.model,
                created_at=h.created_at,
                truncated=h.truncated,
                memo=h.memo,
            )
            for h in items
        ],
        total=total,
    )


@router.post("/history", response_model=HistoryDetailResponse, status_code=201)
async def save_history(
    payload: HistoryCreateRequest,
    token: str = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """校正結果を履歴に保存する (§7.1)."""
    record = create_history(
        db,
        input_text=payload.input_text,
        result=payload.result,
        model=payload.model,
        document_type=payload.document_type,
        memo=payload.memo,
    )
    return _to_detail(record)


@router.get("/history/{history_id}", response_model=HistoryDetailResponse)
async def get_history(
    history_id: int,
    token: str = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """履歴の詳細を取得する."""
    record = get_history_by_id(db, history_id)
    if record is None:
        raise HTTPException(status_code=404, detail="指定された履歴が見つかりません")
    return _to_detail(record)


@router.patch("/history/{history_id}", response_model=HistoryDetailResponse)
async def patch_history(
    history_id: int,
    payload: HistoryUpdateRequest,
    token: str = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """履歴のメモを更新する."""
    record = update_history_memo(db, history_id, payload.memo)
    if record is None:
        raise HTTPException(status_code=404, detail="指定された履歴が見つかりません")
    return _to_detail(record)


@router.delete("/history/{history_id}")
async def delete_history_endpoint(
    history_id: int,
    token: str = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """履歴を1件削除する."""
    if not delete_history(db, history_id):
        raise HTTPException(status_code=404, detail="指定された履歴が見つかりません")
    return {"message": "削除しました"}


@router.delete("/history")
async def delete_all_history_endpoint(
    token: str = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """履歴を全件削除する."""
    count = delete_all_history(db)
    return {"message": f"{count}件の履歴を削除しました"}


def _to_detail(record) -> HistoryDetailResponse:
    """Convert ORM History to HistoryDetailResponse."""
    result_data = json.loads(record.result_json)
    return HistoryDetailResponse(
        id=record.id,
        input_text=record.input_text,
        result=ProofreadResponse(**result_data),
        model=record.model,
        document_type=record.document_type,
        created_at=record.created_at,
        truncated=record.truncated,
        memo=record.memo,
    )
```

- [ ] **Step 4: Register the router in main.py**

In `backend/main.py`, after the proofread router registration (line 145), add:

```python
from routers.history import router as history_router
application.include_router(history_router)
```

- [ ] **Step 5: Run router tests to verify they pass**

Run: `cd backend && pytest tests/test_history.py -k "Router" -v`
Expected: All PASS

- [ ] **Step 6: Run all tests to verify no regression**

Run: `cd backend && pytest -v`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add backend/routers/history.py backend/main.py backend/tests/test_history.py
git commit -m "feat(backend): implement history router with 6 CRUD endpoints"
```

---

## Task 8: Final Verification

- [ ] **Step 1: Run full test suite**

Run: `cd backend && pytest -v`
Expected: All PASS (including existing tests + new history tests)

- [ ] **Step 2: Verify API docs render**

Run: `cd backend && uvicorn main:app --host 127.0.0.1 --port 8000 &`
Open: `http://127.0.0.1:8000/docs`
Verify: All 6 history endpoints appear with correct schemas

- [ ] **Step 3: Stop the dev server**

Run: `kill %1` or Ctrl+C

- [ ] **Step 4: Review the implementation against the design spec checklist**

Verify each requirement from §5.1, §5.4, §7:

- [x] GET /api/history — list with search/filter/pagination
- [x] POST /api/history — save with truncation
- [x] GET /api/history/{id} — detail view
- [x] PATCH /api/history/{id} — update memo
- [x] DELETE /api/history/{id} — delete single
- [x] DELETE /api/history — delete all
- [x] FTS5 ngram full-text search with LIKE fallback
- [x] Query params: q, document_type, date_from, date_to, limit, offset
- [x] 100KB result JSON truncation (keep corrected_text + summary)
- [x] Count limit auto-cleanup (configurable via settings)
- [x] 20MB capacity limit auto-cleanup
- [x] Preview truncated to 50 chars in list
- [x] Auth required on all endpoints
- [x] Proper error responses (404, 401, 422)
