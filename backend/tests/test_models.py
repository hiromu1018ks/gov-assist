import pytest
from datetime import datetime, timezone


def test_history_model_columns(db_session):
    """History テーブルのカラムが正しく定義されている"""
    from models import History
    from sqlalchemy import inspect

    inspector = inspect(db_session.get_bind())
    columns = {c["name"] for c in inspector.get_columns("history")}

    expected_columns = {
        "id", "input_text", "result_json", "model",
        "document_type", "created_at", "memo", "truncated",
    }
    assert expected_columns.issubset(columns)


def test_history_model_create_and_retrieve(db_session):
    """History レコードの作成と取得"""
    from models import History

    record = History(
        input_text="テスト入力",
        result_json='{"corrected_text": "テスト校正済み"}',
        model="kimi-k2.5",
        document_type="official",
        memo="テストメモ",
        truncated=False,
    )
    db_session.add(record)
    db_session.commit()

    retrieved = db_session.query(History).first()
    assert retrieved is not None
    assert retrieved.input_text == "テスト入力"
    assert retrieved.model == "kimi-k2.5"
    assert retrieved.document_type == "official"
    assert retrieved.memo == "テストメモ"
    assert retrieved.truncated is False
    assert retrieved.created_at is not None


def test_history_model_truncated_flag(db_session):
    """truncated フラグが正しく保存される"""
    from models import History

    record = History(
        input_text="A" * 8000,
        result_json='{"corrected_text": "short"}',
        model="kimi-k2.5",
        document_type="email",
        truncated=True,
    )
    db_session.add(record)
    db_session.commit()

    retrieved = db_session.query(History).first()
    assert retrieved.truncated is True


def test_history_model_id_is_int(db_session):
    """id カラムが自動採番の整数である"""
    from models import History

    r1 = History(input_text="1", result_json="{}", model="kimi-k2.5", document_type="other")
    r2 = History(input_text="2", result_json="{}", model="kimi-k2.5", document_type="other")
    db_session.add_all([r1, r2])
    db_session.commit()

    records = db_session.query(History).order_by(History.id).all()
    assert records[0].id == 1
    assert records[1].id == 2
    assert records[1].id > records[0].id


def test_history_model_default_truncated_is_false(db_session):
    """truncated のデフォルト値が False である"""
    from models import History

    record = History(
        input_text="test",
        result_json="{}",
        model="kimi-k2.5",
        document_type="report",
    )
    db_session.add(record)
    db_session.commit()

    retrieved = db_session.query(History).first()
    assert retrieved.truncated is False


class TestSettingsModel:
    def test_settings_model_columns(self, db_session):
        """Settings テーブルのカラムが正しく定義されている"""
        from models import Settings
        from sqlalchemy import inspect

        inspector = inspect(db_session.get_bind())
        columns = {c["name"] for c in inspector.get_columns("settings")}

        expected_columns = {"key", "value"}
        assert expected_columns == columns

    def test_settings_model_create_and_retrieve(self, db_session):
        """Settings レコードの作成と取得"""
        from models import Settings

        record = Settings(key="history_limit", value="50")
        db_session.add(record)
        db_session.commit()

        retrieved = db_session.query(Settings).filter_by(key="history_limit").first()
        assert retrieved is not None
        assert retrieved.value == "50"

    def test_settings_model_key_is_unique(self, db_session):
        """key カラムが一意制約を持つ"""
        from models import Settings
        from sqlalchemy.exc import IntegrityError

        db_session.add(Settings(key="history_limit", value="50"))
        db_session.commit()

        duplicate = Settings(key="history_limit", value="100")
        db_session.add(duplicate)
        with pytest.raises(IntegrityError):
            db_session.commit()
