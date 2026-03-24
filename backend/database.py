import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


# モジュールレベル変数: FTS5 ngram トークナイザ対応状況（起動時に設定）
FTS5_NGRAM_SUPPORTED: bool | None = None


def get_database_url() -> str:
    """Get database URL from environment or use default SQLite path."""
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    # デフォルト: backend/data/govassist.db
    db_dir = Path(__file__).parent / "data"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / "govassist.db"
    return f"sqlite:///{db_path}"


def get_engine(url: str | None = None) -> "Engine":
    """Create SQLAlchemy engine. Ensures parent directory exists."""
    if url is None:
        url = get_database_url()
    # sqlite:// URL の場合、ファイルの親ディレクトリを作成
    if url.startswith("sqlite:///"):
        db_path = url[len("sqlite:///"):]
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(url, connect_args={"check_same_thread": False})


# Base class for ORM models
class Base(DeclarativeBase):
    pass


def init_db(engine=None) -> None:
    """Create all tables. Call once at app startup."""
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(engine)


def get_session_local(engine=None):
    """Create a session factory for the given engine."""
    if engine is None:
        engine = get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Module-level engine and session factory for get_db() dependency
_engine = get_engine()
_SessionLocal = get_session_local(_engine)


def get_db():
    """FastAPI dependency: yield a DB session.

    Uses the default engine. The session is closed after the request.
    """
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    finally:
        session.close()


def check_fts5_ngram_support() -> bool:
    """Check if SQLite FTS5 ngram tokenizer is available.

    Results are cached in the module-level FTS5_NGRAM_SUPPORTED variable
    so Task 10 (History route) can reuse it without re-checking.
    """
    global FTS5_NGRAM_SUPPORTED
    if FTS5_NGRAM_SUPPORTED is not None:
        return FTS5_NGRAM_SUPPORTED

    import sqlite3
    try:
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE VIRTUAL TABLE t USING fts5(x, tokenize='ngram')")
        conn.close()
        FTS5_NGRAM_SUPPORTED = True
        return True
    except Exception:
        FTS5_NGRAM_SUPPORTED = False
        return False


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
