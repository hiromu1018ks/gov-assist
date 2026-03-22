# Task 2: データベースセットアップ Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** SQLAlchemy + SQLite のデータベース基盤を構築し、History テーブルモデル・Alembic マイグレーション・全文検索をセットアップする。

**Architecture:** SQLAlchemy 2.0 スタイル（Mapped・mapped_column）で ORM モデルを定義し、Alembic でマイグレーション管理する。全文検索は FTS5 を前提に設計するが、ngram トークナイザが利用不可な環境では unicode61 にフォールバックする。DB ファイルは `backend/data/govassist.db` に配置し、アプリ起動時に自動で初期化する。

**Tech Stack:** SQLAlchemy 2.0+, Alembic, SQLite (FTS5)

**Design Spec Reference:** §7（校正履歴管理）, §11（ディレクトリ構成）, §5.4（GET /api/history 検索仕様）

**前提条件:** Task 1 完了済み（main.py, schemas.py, requirements.txt, .env.example, logs/ が存在する）

---

## 重要事項: FTS5 ngram トークナイザの環境依存

設計書 §5.4 では FTS5 ngram トークナイザを前提としているが、標準ビルドの SQLite では `ngram` トークナイザが利用できない（確認済み: Python 3.14.3 + SQLite 3.52.0 で `no such tokenizer: ngram`）。

**対応方針:**
- FTS5 テーブル設計は `tokenize='ngram'` をデフォルトとする
- `database.py` で起動時に ngram トークナイザの利用可否をチェックし、モジュールレベル変数 `FTS5_NGRAM_SUPPORTED` にキャッシュする
- 不可の場合は `tokenize='unicode61'` にフォールバックする
- FTS5 仮想テーブルの作成は Task 10（History ルート）で実装する
- LIKE 検索のフォールバックも Task 10 で実装する
- このタスクでは `check_fts5_ngram_support()` とログ出力のみを提供し、実際の FTS5 テーブルは作成しない

---

## ファイル構成

| ファイル | 責務 |
|---------|------|
| `backend/database.py` | SQLAlchemy エンジン・セッションファクトリ・DB 初期化ロジック |
| `backend/models.py` | ORM モデル定義（History テーブル） |
| `backend/alembic.ini` | Alembic 設定ファイル |
| `backend/migrations/env.py` | Alembic マイグレーション環境設定 |
| `backend/migrations/script.py.mako` | マイグレーションスクリプトテンプレート |
| `backend/migrations/versions/001_create_history.py` | 初回マイグレーション（History テーブル + FTS5） |
| `backend/tests/test_database.py` | database.py のテスト |
| `backend/tests/test_models.py` | models.py のテスト |
| `backend/tests/conftest.py` | テスト用 DB セッションフィクスチャ |
| `backend/requirements.txt` | sqlalchemy, alembic を追加 |
| `backend/main.py` | DB 初期化呼び出しを追加 |

---

### Task 2.1: 依存パッケージの追加

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/.env.example`

- [ ] **Step 1: requirements.txt に sqlalchemy と alembic を追加**

```
sqlalchemy>=2.0
alembic>=1.13
```

を `backend/requirements.txt` の末尾に追加する。

- [ ] **Step 1.5: .env.example に DATABASE_URL を追加**

`backend/.env.example` の末尾に以下を追加:

```
# DATABASE_URL=sqlite:///data/govassist.db  # Optional: override default SQLite path
```

- [ ] **Step 2: パッケージをインストール**

Run: `cd backend && pip install -r requirements.txt`
Expected: Successfully installed sqlalchemy, alembic および依存パッケージ

- [ ] **Step 3: インストール確認**

Run: `cd backend && python -c "import sqlalchemy; print(sqlalchemy.__version__)" && python -c "import alembic; print(alembic.__version__)"`
Expected: バージョン番号が表示される

- [ ] **Step 4: Commit**

```bash
git add backend/requirements.txt backend/.env.example
git commit -m "chore(backend): add sqlalchemy and alembic dependencies"
```

---

### Task 2.2: SQLAlchemy データベース設定 (database.py)

**Files:**
- Create: `backend/database.py`

- [ ] **Step 1: テスト用 DB セッションフィクスチャを書く**

`backend/tests/conftest.py` にテスト用のインメモリ DB セッションフィクスチャを追加する。

```python
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def db_engine():
    """インメモリ SQLite エンジン（テスト用）"""
    engine = create_engine("sqlite:///:memory:")
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """テスト用 DB セッション。テストごとにロールバック。

    begin_nested() セーブポイントパターンを使用することで、
    テスト内で session.commit() を呼んでも外側のトランザクションで
    ロールバックされ、テスト間のデータ汚染を防ぐ。
    """
    from database import Base
    Base.metadata.create_all(db_engine)
    connection = db_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    session.begin_nested()

    # セーブポイントが終了したら新しいセーブポイントを開始
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        if trans.nested and not trans._parent.nested:
            sess.begin_nested()

    yield session
    session.close()
    transaction.rollback()
    connection.close()
```

- [ ] **Step 2: database.py のテストを書く**

`backend/tests/test_database.py` を作成する。

```python
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
    # この環境では ngram 非対応が確認済み（Python 3.14.3 + SQLite 3.52.0）
    # ビルド済みの SQLite が ngram をサポートしている場合は True
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
```

- [ ] **Step 3: テストを実行して失敗を確認**

Run: `cd backend && python -m pytest tests/test_database.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'database')

- [ ] **Step 4: database.py を実装**

`backend/database.py` を作成する。

```python
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
```

- [ ] **Step 5: テストを実行して成功を確認**

Run: `cd backend && python -m pytest tests/test_database.py -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add backend/database.py backend/tests/test_database.py backend/tests/conftest.py
git commit -m "feat(backend): add SQLAlchemy database configuration with FTS5 ngram detection"
```

---

### Task 2.3: ORM モデル定義 (models.py)

**Files:**
- Create: `backend/models.py`
- Create: `backend/tests/test_models.py`

- [ ] **Step 1: テストを書く**

`backend/tests/test_models.py` を作成する。

```python
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
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `cd backend && python -m pytest tests/test_models.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'models')

- [ ] **Step 3: models.py を実装**

`backend/models.py` を作成する。

```python
from datetime import datetime, timezone

from sqlalchemy import Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class History(Base):
    __tablename__ = "history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(50), nullable=False)
    document_type: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    truncated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
```

> **設計書 §7.1 との対応:**
> - `input_text`: 入力テキスト（最大 8,000 文字）— バリデーションは API 層で実施
> - `result_json`: 校正結果 JSON（最大 100KB）— バリデーション・切り捨ては API 層で実施
> - `model`: 使用モデル名
> - `document_type`: 文書種別
> - `created_at`: 校正日時（UTC）
> - `memo`: ユーザー追記メモ
> - `truncated`: result_json が切り捨てられたかのフラグ

- [ ] **Step 4: テストを実行して成功を確認**

Run: `cd backend && python -m pytest tests/test_models.py -v`
Expected: ALL PASS

- [ ] **Step 5: 全テストを実行して回帰がないことを確認**

Run: `cd backend && python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add backend/models.py backend/tests/test_models.py
git commit -m "feat(backend): add History ORM model with truncated flag"
```

---

### Task 2.4: Alembic マイグレーション設定

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/migrations/env.py`
- Create: `backend/migrations/script.py.mako`
- Create: `backend/migrations/versions/001_create_history.py`

- [ ] **Step 1: Alembic 初期化**

`backend/migrations/` に移動し、既存の `__init__.py` を残したまま Alembic を初期化する。

Run:
```bash
cd backend
# alembic.ini を手動で配置する（Step 2 で作成）
# migrations/ 以下のテンプレートも手動で作成
```

- [ ] **Step 2: alembic.ini を作成**

`backend/alembic.ini` を作成する。

```ini
[alembic]
script_location = migrations
sqlalchemy.url = sqlite:///data/govassist.db

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 3: migrations/env.py を作成**

`backend/migrations/env.py` を作成する。

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from database import Base, get_database_url
from models import History  # noqa: F401 — ensure model is registered with Base

config = context.config

# sqlalchemy.url を環境変数から取得（開発用）
config.set_main_option("sqlalchemy.url", get_database_url())

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 4: migrations/script.py.mako を作成**

`backend/migrations/script.py.mako` を作成する。

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 5: 初回マイグレーションを作成**

`backend/migrations/versions/001_create_history.py` を作成する。

```python
"""create history table

Revision ID: 001
Revises: None
Create Date: 2026-03-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=50), nullable=False),
        sa.Column("document_type", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column("truncated", sa.Boolean(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_history_created_at", "history", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_history_created_at", table_name="history")
    op.drop_table("history")
```

> **注意:** FTS5 仮想テーブル（全文検索用）は Alembic マイグレーションには含めない。理由:
> 1. FTS5 テーブルの作成には `CREATE VIRTUAL TABLE` 構文が必要で、Alembic の `op.create_table` では対応不可
> 2. ngram トークナイザの環境依存性があるため、マイグレーション時ではなくアプリ起動時に動的に作成する方が適切
> 3. FTS5 テーブルの作成ロジックは Task 10（History ルート）で実装する

- [ ] **Step 6: マイグレーションが正常に実行できることを確認**

Run:
```bash
cd backend && python -c "
from database import get_engine, Base, init_db
from models import History
engine = get_engine('sqlite:///data/govassist.db')
init_db(engine)
from sqlalchemy import inspect
print('Tables:', inspect(engine).get_table_names())
print('OK')
"
```
Expected: `Tables: ['history']` + `OK`

- [ ] **Step 7: 既存の tests/ が全て通ることを確認**

Run: `cd backend && python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 8: Commit**

```bash
git add backend/alembic.ini backend/migrations/ backend/data/ backend/.gitignore
git commit -m "feat(backend): add Alembic migration setup with initial history table"
```

> **注意:** `backend/data/govassist.db` は .gitignore に追加すること。

---

### Task 2.5: main.py への DB 初期化統合

**Files:**
- Modify: `backend/main.py`
- Modify: `backend/.gitignore`

- [ ] **Step 1: .gitignore に data/ ディレクトリを追加**

`backend/.gitignore` に以下を追加:

```
data/
```

- [ ] **Step 2: main.py に DB 初期化を追加**

`backend/main.py` の `setup_logging()` 呼び出しの前に以下を追加:

```python
# DB 初期化（テーブルが存在しない場合は作成）
from database import init_db
init_db()
```

追加後の `main.py` の下部は以下のようになる:

```python
# DB 初期化（テーブルが存在しない場合は作成）
from database import init_db
init_db()

setup_logging()
```

- [ ] **Step 3: アプリが正常に起動することを確認**

Run: `cd backend && python -c "from main import app; print('App loaded OK')"`
Expected: `App loaded OK`

- [ ] **Step 4: 全テストを実行**

Run: `cd backend && python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add backend/main.py backend/.gitignore
git commit -m "feat(backend): integrate DB initialization into app startup"
```

---

## 最終確認

- [ ] **Step 1: 全テストの実行**

Run: `cd backend && python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 2: FTS5 ngram 対応状況のロギング**

`backend/main.py` の DB 初期化後に以下を追加し、起動時に ngram 対応状況をログ出力する:

```python
from database import check_fts5_ngram_support
if check_fts5_ngram_support():
    logger.info("FTS5 ngram tokenizer: supported")
else:
    logger.warning("FTS5 ngram tokenizer: NOT supported. Unicode61 will be used as fallback.")
```

- [ ] **Step 3: ログ出力を確認**

Run: `cd backend && python -c "from main import app; print('OK')"`
Expected: コンソールに `FTS5 ngram tokenizer: NOT supported...` が表示される（この環境では ngram 非対応のため）

- [ ] **Step 4: Final commit**

```bash
git add backend/main.py
git commit -m "feat(backend): log FTS5 ngram tokenizer support status at startup"
```

---

## 成果物のまとめ

Task 2 完了後に存在するファイル:

| ファイル | 状態 | 内容 |
|---------|------|------|
| `backend/database.py` | 新規 | SQLAlchemy エンジン・セッション・DB初期化・FTS5 チェック |
| `backend/models.py` | 新規 | History ORM モデル（truncated フラグ付き） |
| `backend/alembic.ini` | 新規 | Alembic 設定 |
| `backend/migrations/env.py` | 新規 | Alembic マイグレーション環境 |
| `backend/migrations/script.py.mako` | 新規 | マイグレーションスクリプトテンプレート |
| `backend/migrations/versions/001_create_history.py` | 新規 | 初回マイグレーション |
| `backend/tests/test_database.py` | 新規 | database.py のテスト |
| `backend/tests/test_models.py` | 新規 | models.py のテスト |
| `backend/tests/conftest.py` | 変更 | テスト用 DB フィクスチャ追加 |
| `backend/main.py` | 変更 | DB 初期化・FTS5 チェックログ追加 |
| `backend/.gitignore` | 変更 | data/ を追加 |
| `backend/requirements.txt` | 変更 | sqlalchemy, alembic 追加 |
