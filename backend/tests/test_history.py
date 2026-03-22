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


class TestFts5Setup:
    """FTS5 virtual table creation tests."""

    def test_init_fts5_creates_fts_table_when_supported(self, db_engine):
        from database import init_fts5, check_fts5_ngram_support
        if not check_fts5_ngram_support():
            pytest.skip("FTS5 ngram not supported in this environment")
        from sqlalchemy import text
        init_fts5(db_engine)
        with db_engine.connect() as conn:
            result = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='history_fts'")
            )
            assert result.fetchone() is not None

    def test_init_fts5_is_idempotent(self, db_engine):
        from database import init_fts5, check_fts5_ngram_support
        if not check_fts5_ngram_support():
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
        from database import init_fts5, check_fts5_ngram_support
        if not check_fts5_ngram_support():
            pytest.skip("FTS5 ngram not supported in this environment")
        from sqlalchemy import text
        init_fts5(db_engine)
        with db_engine.connect() as conn:
            result = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='trigger' AND name='history_ai'")
            )
            assert result.fetchone() is not None


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
