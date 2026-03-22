# Task 8: Models & Settings ルート 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `GET /api/models` と `GET/PUT /api/settings` エンドポイントを実装し、モデル設定テーブルの参照とサーバー側設定（履歴保存件数上限）の CRUD を提供する。

**Architecture:** `services/ai_client.py` に既存の `MODEL_CONFIGS` 辞書を `GET /api/models` で公開。サーバー設定は `settings` テーブル（キーバリューストア）で永続化し、`GET/PUT /api/settings` で操作。DB セッションは `database.py` に `get_db()` 依存関係を追加してルーターに注入する。ルーターは `main.py` の `create_app()` に登録。**循環インポートを避けるため、`verify_token` と `get_app_token` を `backend/dependencies.py` に抽出し、`main.py` と各ルーターはそこから import する。**

**Tech Stack:** FastAPI, SQLAlchemy (SQLite), Pydantic, Alembic

---

## ファイル構成

| 操作 | ファイル | 責務 |
|------|---------|------|
| Create | `backend/dependencies.py` | `verify_token`, `get_app_token` を `main.py` から抽出 |
| Create | `backend/routers/models_router.py` | `GET /api/models` エンドポイント |
| Create | `backend/routers/settings.py` | `GET/PUT /api/settings` エンドポイント |
| Create | `backend/tests/test_models_router.py` | models エンドポイントのテスト |
| Create | `backend/tests/test_settings.py` | settings エンドポイントのテスト |
| Create | `backend/migrations/versions/002_create_settings.py` | settings テーブルの Alembic マイグレーション |
| Modify | `backend/schemas.py` | `ModelInfoResponse`, `SettingsResponse`, `SettingsUpdateRequest` 追加 |
| Modify | `backend/models.py` | `Settings` ORM モデル追加 |
| Modify | `backend/database.py` | `get_db()` 依存関係追加 |
| Modify | `backend/main.py` | `verify_token` を `dependencies.py` に移動、ルーター登録 |

---

## Task 0: verify_token を dependencies.py に抽出（循環インポート解消）

**Files:**
- Create: `backend/dependencies.py`
- Modify: `backend/main.py`

### ステップ 0-1: dependencies.py を作成

`backend/dependencies.py` を作成:

```python
"""Shared FastAPI dependencies — extracted from main.py to avoid circular imports."""
import os
import hmac

from fastapi import Depends, HTTPException, Request


def get_app_token() -> str:
    """Retrieve the APP_TOKEN from environment."""
    return os.getenv("APP_TOKEN", "")


async def verify_token(request: Request, app_token: str = Depends(get_app_token)) -> str:
    """Validate Bearer token from Authorization header.

    Used as a FastAPI dependency: `Depends(verify_token)`.
    Returns the validated token string on success.
    Raises HTTPException on failure.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="認証トークンが不足しています")

    token = auth_header[7:]  # Skip "Bearer " prefix (7 chars)

    if not app_token:
        raise HTTPException(
            status_code=500,
            detail="サーバー設定が不完全です（APP_TOKEN未設定）",
        )

    if not hmac.compare_digest(token, app_token):
        raise HTTPException(status_code=401, detail="認証トークンが一致しません")

    return token
```

### ステップ 0-2: main.py を修正 — verify_token を dependencies から import に変更

`backend/main.py` で以下の変更を行う:

1. `get_app_token` と `verify_token` の定義を削除（67-94行目）
2. 冒頭の import に追加:

```python
from dependencies import verify_token, get_app_token
```

### ステップ 0-3: test_auth.py の import を修正

`backend/tests/test_auth.py` の import 行を変更:

```python
from dependencies import verify_token, get_app_token
```

### ステップ 0-4: 全テストを実行

Run: `cd backend && pytest tests/ -v`
Expected: 全テスト PASS（既存の auth テストが dependencies 経由でも動作することを確認）

### ステップ 0-5: コミット

```bash
git add backend/dependencies.py backend/main.py backend/tests/test_auth.py
git commit -m "refactor(backend): extract verify_token to dependencies.py to avoid circular imports"
```

---

## Task 1: Settings ORM モデルと Pydantic スキーマ追加

**Files:**
- Modify: `backend/models.py`
- Modify: `backend/schemas.py`
- Test: `backend/tests/test_models.py` (追加)

### ステップ 1-1: Settings ORM モデルのテストを書く

`backend/tests/test_models.py` に以下を追加する（既存テストはそのまま残す）:

```python
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
```

### ステップ 1-2: テストを実行して失敗を確認

Run: `cd backend && pytest tests/test_models.py::TestSettingsModel -v`
Expected: FAIL（`ImportError` または `NoSuchTableError`）

### ステップ 1-3: Settings ORM モデルを実装

`backend/models.py` に以下を追加:

```python
class Settings(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[str] = mapped_column(String(200), nullable=False)
```

### ステップ 1-4: テストを実行してパスを確認

Run: `cd backend && pytest tests/test_models.py::TestSettingsModel -v`
Expected: PASS

### ステップ 1-5: コミット

```bash
git add backend/models.py backend/tests/test_models.py
git commit -m "feat(backend): add Settings ORM model with key/value store"
```

---

## Task 2: Pydantic スキーマ追加（Models & Settings）

**Files:**
- Modify: `backend/schemas.py`
- Test: `backend/tests/test_schemas.py` (追加)

### ステップ 2-1: スキーマのテストを書く

`backend/tests/test_schemas.py` に以下を追加:

```python
class TestModelInfoResponse:
    def test_model_info_response_valid(self):
        from schemas import ModelInfoResponse
        m = ModelInfoResponse(
            model_id="kimi-k2.5",
            display_name="Kimi K2.5",
            max_tokens=4096,
            temperature=0.3,
            max_input_chars=8000,
            json_forced=True,
        )
        assert m.model_id == "kimi-k2.5"
        assert m.display_name == "Kimi K2.5"

    def test_models_response_list(self):
        from schemas import ModelInfoResponse, ModelsResponse
        models = ModelsResponse(models=[
            ModelInfoResponse(
                model_id="kimi-k2.5",
                display_name="Kimi K2.5",
                max_tokens=4096,
                temperature=0.3,
                max_input_chars=8000,
                json_forced=True,
            )
        ])
        assert len(models.models) == 1
        assert models.models[0].model_id == "kimi-k2.5"


class TestSettingsResponse:
    def test_settings_response_valid(self):
        from schemas import SettingsResponse
        s = SettingsResponse(history_limit=50)
        assert s.history_limit == 50

    def test_settings_response_defaults(self):
        from schemas import SettingsResponse
        s = SettingsResponse()
        assert s.history_limit == 50


class TestSettingsUpdateRequest:
    def test_settings_update_valid(self):
        from schemas import SettingsUpdateRequest
        s = SettingsUpdateRequest(history_limit=100)
        assert s.history_limit == 100

    def test_settings_update_below_minimum(self):
        from schemas import SettingsUpdateRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            SettingsUpdateRequest(history_limit=0)

    def test_settings_update_above_maximum(self):
        from schemas import SettingsUpdateRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            SettingsUpdateRequest(history_limit=201)
```

### ステップ 2-2: テストを実行して失敗を確認

Run: `cd backend && pytest tests/test_schemas.py::TestModelInfoResponse tests/test_schemas.py::TestSettingsResponse tests/test_schemas.py::TestSettingsUpdateRequest -v`
Expected: FAIL（`ImportError`）

### ステップ 2-3: Pydantic スキーマを実装

`backend/schemas.py` の末尾に追加:

```python
class ModelInfoResponse(BaseModel):
    model_id: str
    display_name: str
    max_tokens: int
    temperature: float
    max_input_chars: int
    json_forced: bool


class ModelsResponse(BaseModel):
    models: list[ModelInfoResponse]


class SettingsResponse(BaseModel):
    history_limit: int = 50


class SettingsUpdateRequest(BaseModel):
    history_limit: int = Field(ge=1, le=200)
```

### ステップ 2-4: テストを実行してパスを確認

Run: `cd backend && pytest tests/test_schemas.py::TestModelInfoResponse tests/test_schemas.py::TestSettingsResponse tests/test_schemas.py::TestSettingsUpdateRequest -v`
Expected: PASS

### ステップ 2-5: コミット

```bash
git add backend/schemas.py backend/tests/test_schemas.py
git commit -m "feat(backend): add Pydantic schemas for models and settings endpoints"
```

---

## Task 3: DB セッション依存関係（get_db）

**Files:**
- Modify: `backend/database.py`
- Modify: `backend/tests/conftest.py`

### ステップ 3-1: conftest.py に app_client フィクスチャを追加

`backend/tests/conftest.py` に以下を追加（既存フィクスチャはそのまま残す）:

```python
@pytest.fixture
def app_client(db_session):
    """認証付き TestClient。DB セッションを注入する。"""
    from fastapi.testclient import TestClient
    from main import create_app
    from dependencies import get_app_token
    from database import get_db

    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # セッションは db_session フィクスチャで管理

    app = create_app(enable_origin_check=False)
    app.dependency_overrides[get_app_token] = lambda: "test-secret-token"
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
```

**注意:** トークン値は `test_auth.py` と同じ `"test-secret-token"` に統一する。

### ステップ 3-2: get_db を実装

`backend/database.py` に以下を追加:

```python
def get_db():
    """FastAPI dependency: yield a DB session.

    Uses the default engine. The session is closed after the request.
    """
    engine = get_engine()
    SessionLocal = get_session_local(engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
```

### ステップ 3-3: 全テストを実行

Run: `cd backend && pytest tests/ -v`
Expected: 全テスト PASS（`get_db` の動作は Task 5 の settings ルーターテストで統合検証されるため、単体テストは不要）

### ステップ 3-4: コミット

```bash
git add backend/database.py backend/tests/conftest.py
git commit -m "feat(backend): add get_db dependency and app_client test fixture"
```

---

## Task 4: Models ルーター (`GET /api/models`)

**Files:**
- Create: `backend/routers/models_router.py`
- Create: `backend/tests/test_models_router.py`
- Modify: `backend/main.py`

### ステップ 4-1: テストを書く

`backend/tests/test_models_router.py` を作成:

```python
"""Tests for GET /api/models endpoint (§4.2, §5.1)."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(app_client):
    return app_client


class TestGetModels:
    def test_returns_200_with_auth(self, client):
        resp = client.get(
            "/api/models",
            headers={"Authorization": "Bearer test-secret-token"},
        )
        assert resp.status_code == 200

    def test_returns_models_list(self, client):
        resp = client.get(
            "/api/models",
            headers={"Authorization": "Bearer test-secret-token"},
        )
        data = resp.json()
        assert "models" in data
        assert isinstance(data["models"], list)
        assert len(data["models"]) >= 1

    def test_kimi_k25_in_response(self, client):
        resp = client.get(
            "/api/models",
            headers={"Authorization": "Bearer test-secret-token"},
        )
        models = resp.json()["models"]
        kimi = next(m for m in models if m["model_id"] == "kimi-k2.5")
        assert kimi["display_name"] == "Kimi K2.5"
        assert kimi["max_tokens"] == 4096
        assert kimi["temperature"] == 0.3
        assert kimi["max_input_chars"] == 8000
        assert kimi["json_forced"] is True

    def test_model_fields_are_complete(self, client):
        resp = client.get(
            "/api/models",
            headers={"Authorization": "Bearer test-secret-token"},
        )
        model = resp.json()["models"][0]
        expected_keys = {"model_id", "display_name", "max_tokens", "temperature", "max_input_chars", "json_forced"}
        assert set(model.keys()) == expected_keys

    def test_returns_401_without_auth(self, client):
        resp = client.get("/api/models")
        assert resp.status_code == 401

    def test_returns_401_with_wrong_token(self, client):
        resp = client.get(
            "/api/models",
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert resp.status_code == 401
```

### ステップ 4-2: テストを実行して失敗を確認

Run: `cd backend && pytest tests/test_models_router.py -v`
Expected: FAIL（404 — ルーター未登録のため）

### ステップ 4-3: ルーターを実装

`backend/routers/models_router.py` を作成:

```python
"""GET /api/models — 利用可能な AI モデル一覧 (§4.2, §5.1)."""
from fastapi import APIRouter, Depends

from dependencies import verify_token
from schemas import ModelsResponse, ModelInfoResponse
from services.ai_client import MODEL_CONFIGS

router = APIRouter(prefix="/api", tags=["models"])


@router.get("/models", response_model=ModelsResponse)
async def get_models(token: str = Depends(verify_token)):
    """Return all available AI models from the model config table."""
    models = [
        ModelInfoResponse(
            model_id=model_id,
            display_name=config.display_name,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            max_input_chars=config.max_input_chars,
            json_forced=config.json_forced,
        )
        for model_id, config in MODEL_CONFIGS.items()
    ]
    return ModelsResponse(models=models)
```

### ステップ 4-4: main.py にルーターを登録

`backend/main.py` の `create_app()` 内、health エンドポイントの後に以下を追加:

```python
    from routers.models_router import router as models_router
    application.include_router(models_router)
```

### ステップ 4-5: テストを実行してパスを確認

Run: `cd backend && pytest tests/test_models_router.py -v`
Expected: PASS

### ステップ 4-6: 既存テストもパスすることを確認

Run: `cd backend && pytest tests/ -v`
Expected: 全テスト PASS

### ステップ 4-7: コミット

```bash
git add backend/routers/models_router.py backend/tests/test_models_router.py backend/main.py
git commit -m "feat(backend): add GET /api/models endpoint with auth"
```

---

## Task 5: Settings ルーター (`GET/PUT /api/settings`)

**Files:**
- Create: `backend/routers/settings.py`
- Create: `backend/tests/test_settings.py`
- Modify: `backend/main.py`

### ステップ 5-1: テストを書く

`backend/tests/test_settings.py` を作成:

```python
"""Tests for GET/PUT /api/settings endpoint (§3.4, §5.1)."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-secret-token"}


@pytest.fixture
def client(app_client):
    return app_client


class TestGetSettings:
    def test_returns_200_with_auth(self, client, auth_headers):
        resp = client.get("/api/settings", headers=auth_headers)
        assert resp.status_code == 200

    def test_returns_history_limit(self, client, auth_headers):
        resp = client.get("/api/settings", headers=auth_headers)
        data = resp.json()
        assert "history_limit" in data
        assert isinstance(data["history_limit"], int)

    def test_default_history_limit_is_50(self, client, auth_headers):
        """DB に設定がない場合、デフォルト値 50 を返す"""
        resp = client.get("/api/settings", headers=auth_headers)
        assert resp.json()["history_limit"] == 50

    def test_returns_401_without_auth(self, client):
        resp = client.get("/api/settings")
        assert resp.status_code == 401


class TestPutSettings:
    def test_update_history_limit(self, client, auth_headers):
        resp = client.put(
            "/api/settings",
            json={"history_limit": 100},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["history_limit"] == 100

    def test_update_is_persisted(self, client, auth_headers):
        """更新後の GET で新しい値が返る"""
        client.put(
            "/api/settings",
            json={"history_limit": 75},
            headers=auth_headers,
        )
        resp = client.get("/api/settings", headers=auth_headers)
        assert resp.json()["history_limit"] == 75

    def test_update_to_minimum(self, client, auth_headers):
        resp = client.put(
            "/api/settings",
            json={"history_limit": 1},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["history_limit"] == 1

    def test_update_to_maximum(self, client, auth_headers):
        resp = client.put(
            "/api/settings",
            json={"history_limit": 200},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["history_limit"] == 200

    def test_update_below_minimum_returns_422(self, client, auth_headers):
        resp = client.put(
            "/api/settings",
            json={"history_limit": 0},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_update_above_maximum_returns_422(self, client, auth_headers):
        resp = client.put(
            "/api/settings",
            json={"history_limit": 201},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_update_missing_field_returns_422(self, client, auth_headers):
        resp = client.put(
            "/api/settings",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_update_without_auth_returns_401(self, client):
        resp = client.put(
            "/api/settings",
            json={"history_limit": 100},
        )
        assert resp.status_code == 401

    def test_update_with_wrong_token_returns_401(self, client):
        resp = client.put(
            "/api/settings",
            json={"history_limit": 100},
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert resp.status_code == 401

    def test_invalid_field_returns_422(self, client, auth_headers):
        resp = client.put(
            "/api/settings",
            json={"history_limit": "not-a-number"},
            headers=auth_headers,
        )
        assert resp.status_code == 422
```

### ステップ 5-2: テストを実行して失敗を確認

Run: `cd backend && pytest tests/test_settings.py -v`
Expected: FAIL（404 — ルーター未登録のため）

### ステップ 5-3: ルーターを実装

`backend/routers/settings.py` を作成:

```python
"""GET/PUT /api/settings — サーバー側設定 CRUD (§3.4, §5.1)."""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from dependencies import verify_token
from models import Settings
from schemas import SettingsResponse, SettingsUpdateRequest

logger = logging.getLogger("govassist")

router = APIRouter(prefix="/api", tags=["settings"])

DEFAULT_HISTORY_LIMIT = 50


def _get_setting(db: Session, key: str, default: str) -> str:
    """Get a setting value from DB, or return default."""
    row = db.query(Settings).filter_by(key=key).first()
    return row.value if row else default


def _set_setting(db: Session, key: str, value: str) -> None:
    """Set a setting value in DB (upsert)."""
    row = db.query(Settings).filter_by(key=key).first()
    if row:
        row.value = value
    else:
        db.add(Settings(key=key, value=value))


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(
    token: str = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Get server-side settings. Returns defaults for unset values."""
    raw = _get_setting(db, "history_limit", str(DEFAULT_HISTORY_LIMIT))
    try:
        history_limit = int(raw)
    except (ValueError, TypeError):
        logger.warning("Invalid history_limit value in DB: %r, using default", raw)
        history_limit = DEFAULT_HISTORY_LIMIT
    return SettingsResponse(history_limit=history_limit)


@router.put("/settings", response_model=SettingsResponse)
async def update_settings(
    payload: SettingsUpdateRequest,
    token: str = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Update server-side settings."""
    _set_setting(db, "history_limit", str(payload.history_limit))
    db.commit()
    return SettingsResponse(history_limit=payload.history_limit)
```

### ステップ 5-4: main.py にルーターを登録

`backend/main.py` の `create_app()` 内、models_router 登録の後に以下を追加:

```python
    from routers.settings import router as settings_router
    application.include_router(settings_router)
```

### ステップ 5-5: テストを実行してパスを確認

Run: `cd backend && pytest tests/test_settings.py -v`
Expected: PASS

### ステップ 5-6: 既存テストもパスすることを確認

Run: `cd backend && pytest tests/ -v`
Expected: 全テスト PASS

### ステップ 5-7: コミット

```bash
git add backend/routers/settings.py backend/tests/test_settings.py backend/main.py
git commit -m "feat(backend): add GET/PUT /api/settings endpoint with auth"
```

---

## Task 6: Alembic マイグレーション & 統合確認

**Files:**
- Create: `backend/migrations/versions/002_create_settings.py`

### ステップ 6-1: マイグレーションファイルを作成

`backend/migrations/versions/002_create_settings.py` を作成:

```python
"""create settings table

Revision ID: 002
Revises: 001
Create Date: 2026-03-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "settings",
        sa.Column("key", sa.String(length=50), nullable=False),
        sa.Column("value", sa.String(length=200), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("settings")
```

### ステップ 6-2: マイグレーションが実行可能であることを確認

Run: `cd backend && alembic upgrade head`
Expected: 成功（"Running upgrade 001 -> 002, create settings table"）

### ステップ 6-3: 全テストを実行

Run: `cd backend && pytest tests/ -v`
Expected: 全テスト PASS（テストはインメモリ SQLite + `Base.metadata.create_all()` を使用するため、Alembic に依存しない）

### ステップ 6-4: コミット

```bash
git add backend/migrations/versions/002_create_settings.py
git commit -m "feat(backend): add Alembic migration for settings table"
```

---

## 最終確認

全タスク完了後、以下を実行して全体の動作確認を行う:

```bash
cd backend && pytest tests/ -v --tb=short
```

全テストが PASS することを確認する。
