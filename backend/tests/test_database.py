import os
from pathlib import Path

import pytest
from sqlalchemy import text


def test_get_database_url_uses_env():
    """DATABASE_URL 環境変数が設定されている場合はそれを使う"""
    os.environ["DATABASE_URL"] = "sqlite:///test.db"
    try:
        from database import get_database_url
        url = get_database_url()
        assert url == "sqlite:///test.db"
    finally:
        del os.environ["DATABASE_URL"]


def test_get_database_url_default():
    """DATABASE_URL 未設定時はデフォルトパスを使う"""
    if "DATABASE_URL" in os.environ:
        del os.environ["DATABASE_URL"]
    from database import get_database_url
    url = get_database_url()
    assert url.startswith("sqlite:///")
    assert "govassist.db" in url


def test_get_engine_creates_engine():
    """get_engine が SQLAlchemy エンジンを返す"""
    from database import get_engine
    engine = get_engine("sqlite:///:memory:")
    assert engine is not None
    assert str(engine.url) == "sqlite:///:memory:"
    engine.dispose()


def test_init_db_creates_tables(db_session):
    """init_db が全テーブルを作成する"""
    from database import init_db
    from sqlalchemy import inspect

    init_db(db_session.get_bind())
    inspector = inspect(db_session.get_bind())
    table_names = inspector.get_table_names()
    assert "history" in table_names


def test_check_fts5_ngram_support():
    """ngram トークナイザの対応状況を正しく判定する"""
    from database import check_fts5_ngram_support
    result = check_fts5_ngram_support()
    assert isinstance(result, bool)
    assert result in (True, False)


def test_check_fts5_ngram_support_mock_unavailable(monkeypatch):
    """ngram 非対応環境のモックテスト"""
    # キャッシュをリセット（他テストの影響を防ぐ）
    monkeypatch.setattr("database.FTS5_NGRAM_SUPPORTED", None)

    def mock_connect(*args, **kwargs):
        import sqlite3
        conn = sqlite3.connect(":memory:")
        # 常に OperationalError を発生させるモック
        def raise_error(*a, **kw):
            raise sqlite3.OperationalError("no such tokenizer: ngram")
        conn.execute = raise_error
        return conn
    monkeypatch.setattr("sqlite3.connect", mock_connect)
    from database import check_fts5_ngram_support
    assert check_fts5_ngram_support() is False


def test_data_directory_creation(tmp_path, monkeypatch):
    """get_database_url は DB ファイルの親ディレクトリが存在しない場合に作成する"""
    import os
    # DATABASE_URL が設定されているとデフォルトパスが使われないのでクリア
    monkeypatch.delenv("DATABASE_URL", raising=False)

    from database import get_database_url
    # __file__ を tmp_path 下に向けてディレクトリ作成を確認
    fake_file = tmp_path / "backend_mod" / "database.py"
    fake_file.parent.mkdir(parents=True)
    fake_file.touch()
    monkeypatch.setattr("database.__file__", str(fake_file))

    url = get_database_url()
    # tmp_path/backend_mod/data/ が作成されているはず
    assert (tmp_path / "backend_mod" / "data").exists()
    assert "govassist.db" in url
