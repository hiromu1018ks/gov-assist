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
