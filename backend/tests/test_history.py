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
