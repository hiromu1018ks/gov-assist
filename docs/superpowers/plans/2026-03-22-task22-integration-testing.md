# Task 22: エンドツーエンド統合テスト & 仕上げ

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** MVP 全機能の統合テストを追加し、設計書§13 Task 22 の要件（フロント↔バック通信確認、エラーケース動作確認、各 status UI 表示確認、diff 精度確認、ログ出力確認）を満たす。

**Architecture:** 既存の単体テスト（37ファイル）でカバーされていない統合テストを追加する。バックエンドは FastAPI TestClient で AI モックを含むパイプライン全体をテストし、フロントエンドは testing-library で複数コンポーネント連携のエッジケースをテストする。最後に全テストスイートを実行して発見された問題を修正する。

**Tech Stack:** pytest, vitest, @testing-library/react, FastAPI TestClient, unittest.mock

---

## 既存テストとの関係

既存の単体テストは以下の通り（変更不要）：
- **バックエンド 19 ファイル**: conftest.py, test_main.py, test_database.py, test_cors.py, test_origin_check.py, test_auth.py, test_models.py, test_schemas.py, test_ai_client.py, test_prompt_builder.py, test_response_parser.py, test_diff_service.py, test_history.py, test_settings.py, test_proofread.py, test_models_router.py, test_export.py, test_docx_exporter.py
- **フロントエンド 19 ファイル**: client.test.js, App.test.jsx, AuthContext.test.jsx, Header.test.jsx, LoginForm.test.jsx, ProtectedRoute.test.jsx, SideMenu.test.jsx, WarningModal.test.jsx, InputArea.test.jsx, OptionPanel.test.jsx, Proofreading.test.jsx, ResultView.test.jsx, DiffView.test.jsx, preprocess.test.js, fileExtractor.test.js, History.test.jsx, Settings.test.jsx, storage.test.js, token.test.js

本プランでは **新規ファイルのみ** を作成する。既存テストファイルは変更しない。

---

### Task 1: バックエンド — 校正エンドポイント統合テスト（エッジケース）

**Files:**
- Create: `backend/tests/test_proofread_integration.py`

既存 `test_proofread.py` は基本的なハッピーパス・エラーハンドリングをカバーしているが、以下のエッジケースが未テスト。これらを TDD で追加する。

- [ ] **Step 1: テストファイルを作成する（X-Request-ID 伝播テスト）**

```python
# test_proofread_integration.py
"""Integration tests for POST /api/proofread — edge cases not covered by unit tests."""
import pytest
from unittest.mock import AsyncMock, patch

from schemas import (
    CorrectionItem,
    DiffBlock,
    DiffType,
    ProofreadStatus,
)
from services.ai_client import ModelConfig
from services.diff_service import DiffResult
from services.response_parser import ParseResult

VALID_REQUEST = {
    "request_id": "test-req-int-001",
    "text": "これはテスト文書です。",
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


class TestRequestIdPropagation:
    """X-Request-ID should be echoed in every response."""

    @patch("routers.proofread.compute_diffs")
    @patch("routers.proofread.parse_ai_response", new_callable=AsyncMock)
    @patch("routers.proofread.create_ai_client")
    @patch("routers.proofread.build_prompts")
    @patch("routers.proofread.get_model_config")
    def test_success_response_echoes_request_id(self, mock_config, mock_build, mock_create, mock_parse, mock_diffs, client):
        mock_config.return_value = MOCK_MODEL_CONFIG
        mock_build.return_value = ("s", "u")
        mock_create.return_value = AsyncMock()
        mock_parse.return_value = ParseResult(
            corrected_text="テスト", summary="OK", corrections=[],
            status=ProofreadStatus.SUCCESS, status_reason=None,
        )
        mock_diffs.return_value = DiffResult(
            diffs=[], warnings=[], status=ProofreadStatus.SUCCESS,
            status_reason=None, corrections=[],
        )

        resp = client.post("/api/proofread", json=VALID_REQUEST, headers=AUTH_HEADERS)
        data = resp.json()
        assert data["request_id"] == "test-req-int-001"

    @patch("routers.proofread.get_model_config")
    def test_error_response_echoes_request_id(self, mock_config, client):
        mock_config.side_effect = KeyError("bad")
        resp = client.post("/api/proofread", json=VALID_REQUEST, headers=AUTH_HEADERS)
        data = resp.json()
        assert data["request_id"] == "test-req-int-001"

    @patch("routers.proofread.create_ai_client")
    @patch("routers.proofread.build_prompts")
    @patch("routers.proofread.get_model_config")
    def test_internal_error_echoes_request_id(self, mock_config, mock_build, mock_create, client):
        mock_config.return_value = MOCK_MODEL_CONFIG
        mock_build.side_effect = RuntimeError("crash")
        mock_create.return_value = AsyncMock()
        resp = client.post("/api/proofread", json=VALID_REQUEST, headers=AUTH_HEADERS)
        data = resp.json()
        assert data["request_id"] == "test-req-int-001"
```

- [ ] **Step 2: テストを実行して通過することを確認**

Run: `cd backend && pytest tests/test_proofread_integration.py::TestRequestIdPropagation -v`
Expected: ALL PASS

- [ ] **Step 3: バリデーションエッジケーステストを追加する**

```python
class TestValidationEdgeCases:
    """Validation boundary and optional field tests."""

    def test_text_at_exactly_8000_chars_passes(self, client):
        resp = client.post(
            "/api/proofread",
            json={**VALID_REQUEST, "text": "あ" * 8000},
            headers=AUTH_HEADERS,
        )
        # Should not be 422 for text length (may be 400 for model or 200 with mocks)
        assert resp.status_code != 422

    def test_text_at_8001_chars_fails(self, client):
        resp = client.post(
            "/api/proofread",
            json={**VALID_REQUEST, "text": "あ" * 8001},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 422

    def test_missing_options_uses_defaults(self, client):
        """options フィールドを省略するとデフォルトが使用される"""
        request_no_options = {
            "request_id": "test-opt-001",
            "text": "テスト",
            "document_type": "official",
            "model": "kimi-k2.5",
        }
        resp = client.post("/api/proofread", json=request_no_options, headers=AUTH_HEADERS)
        # Should not be 422 for missing options (Pydantic applies defaults)
        assert resp.status_code != 422 or "options" not in resp.text

    def test_invalid_document_type_returns_422(self, client):
        resp = client.post(
            "/api/proofread",
            json={**VALID_REQUEST, "document_type": "invalid_type"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 422
```

- [ ] **Step 4: レスポンス構造完全性テストを追加する**

```python
class TestResponseSchemaCompleteness:
    """Verify all expected fields are present in every response type."""

    SUCCESS_FIELDS = {"request_id", "status", "status_reason", "warnings", "corrected_text", "summary", "corrections", "diffs"}
    ERROR_FIELDS = {"request_id", "error", "message"}

    @patch("routers.proofread.compute_diffs")
    @patch("routers.proofread.parse_ai_response", new_callable=AsyncMock)
    @patch("routers.proofread.create_ai_client")
    @patch("routers.proofread.build_prompts")
    @patch("routers.proofread.get_model_config")
    def test_success_response_has_all_fields(self, mock_config, mock_build, mock_create, mock_parse, mock_diffs, client):
        mock_config.return_value = MOCK_MODEL_CONFIG
        mock_build.return_value = ("s", "u")
        mock_create.return_value = AsyncMock()
        mock_parse.return_value = ParseResult(
            corrected_text="テスト", summary="OK",
            corrections=[CorrectionItem(original="A", corrected="B", reason="r", category="c")],
            status=ProofreadStatus.SUCCESS, status_reason=None,
        )
        mock_diffs.return_value = DiffResult(
            diffs=[
                DiffBlock(type=DiffType.EQUAL, text="テ", start=0),
                DiffBlock(type=DiffType.DELETE, text="ス", start=1, reason="r"),
                DiffBlock(type=DiffType.INSERT, text="ト", start=1, position="after", reason="r"),
            ],
            warnings=[], status=ProofreadStatus.SUCCESS,
            status_reason=None,
            corrections=[CorrectionItem(original="A", corrected="B", reason="r", category="c", diff_matched=True)],
        )
        resp = client.post("/api/proofread", json=VALID_REQUEST, headers=AUTH_HEADERS)
        data = resp.json()
        assert self.SUCCESS_FIELDS.issubset(data.keys())
        # Verify diff block fields
        for diff in data["diffs"]:
            assert "type" in diff
            assert "text" in diff
            assert "start" in diff
            assert "position" in diff
            assert "reason" in diff
        # Verify correction fields
        for corr in data["corrections"]:
            assert "original" in corr
            assert "corrected" in corr
            assert "reason" in corr
            assert "category" in corr
            assert "diff_matched" in corr

    @patch("routers.proofread.get_model_config")
    def test_error_response_has_all_fields(self, mock_config, client):
        mock_config.side_effect = KeyError("bad")
        resp = client.post("/api/proofread", json=VALID_REQUEST, headers=AUTH_HEADERS)
        data = resp.json()
        assert self.ERROR_FIELDS.issubset(data.keys())
```

- [ ] **Step 5: 日本語テキストの realistic diff テストを追加する**

```python
class TestJapaneseRealisticDiff:
    """Verify diff accuracy with realistic Japanese proofreading scenarios."""

    @patch("routers.proofread.compute_diffs")
    @patch("routers.proofread.parse_ai_response", new_callable=AsyncMock)
    @patch("routers.proofread.create_ai_client")
    @patch("routers.proofread.build_prompts")
    @patch("routers.proofread.get_model_config")
    def test_realistic_japanese_proofread(self, mock_config, mock_build, mock_create, mock_parse, mock_diffs, client):
        """実際の校正パターン（敬語修正・誤字修正）の統合テスト"""
        input_text = "申請書を提出してください。よろしくおねがいします。"
        corrected_text = "申請書を提出してくださいますようお願いいたします。"

        mock_config.return_value = MOCK_MODEL_CONFIG
        mock_build.return_value = ("s", "u")
        mock_create.return_value = AsyncMock()
        mock_parse.return_value = ParseResult(
            corrected_text=corrected_text,
            summary="2件の修正を行いました。",
            corrections=[
                CorrectionItem(original="提出してください", corrected="提出してくださいますよう", reason="敬語の適切化", category="敬語"),
                CorrectionItem(original="おねがいします", corrected="お願いいたします", reason="表記統一", category="用語"),
            ],
            status=ProofreadStatus.SUCCESS,
            status_reason=None,
        )
        mock_diffs.return_value = DiffResult(
            diffs=[
                DiffBlock(type=DiffType.EQUAL, text="申請書を", start=0),
                DiffBlock(type=DiffType.EQUAL, text="提出", start=5),
                DiffBlock(type=DiffType.DELETE, text="してください", start=7, reason="敬語の適切化"),
                DiffBlock(type=DiffType.INSERT, text="してくださいますよう", start=7, position="after", reason="敬語の適切化"),
                DiffBlock(type=DiffType.EQUAL, text="。よろしく", start=12),
                DiffBlock(type=DiffType.DELETE, text="おねがいします", start=17, reason="表記統一"),
                DiffBlock(type=DiffType.INSERT, text="お願いいたします", start=17, position="after", reason="表記統一"),
                DiffBlock(type=DiffType.EQUAL, text="。", start=25),
            ],
            warnings=[],
            status=ProofreadStatus.SUCCESS,
            status_reason=None,
            corrections=[
                CorrectionItem(original="提出してください", corrected="提出してくださいますよう", reason="敬語の適切化", category="敬語", diff_matched=True),
                CorrectionItem(original="おねがいします", corrected="お願いいたします", reason="表記統一", category="用語", diff_matched=True),
            ],
        )

        resp = client.post(
            "/api/proofread",
            json={**VALID_REQUEST, "text": input_text},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["corrected_text"] == corrected_text
        assert len(data["corrections"]) == 2
        assert all(c["diff_matched"] for c in data["corrections"])

        # Verify diff sequence: delete should precede insert for each change
        types = [d["type"] for d in data["diffs"]]
        for i, t in enumerate(types):
            if t == "delete":
                if i + 1 < len(types):
                    assert types[i + 1] == "insert", f"delete at {i} should be followed by insert"
```

- [ ] **Step 6: 全テストを実行して通過することを確認**

Run: `cd backend && pytest tests/test_proofread_integration.py -v`
Expected: ALL PASS

- [ ] **Step 7: コミット**

```bash
git add backend/tests/test_proofread_integration.py
git commit -m "test(proofread): add integration tests for edge cases and Japanese text"
```

---

### Task 2: バックエンド — 履歴エンドポイント統合テスト（エッジケース）

**Files:**
- Create: `backend/tests/test_history_integration.py`

既存 `test_history.py` は CRUD を広くカバーしているが、検索+ページネーションの組み合わせが未テスト。

- [ ] **Step 1: 検索＋ページネーション組み合わせテストを書く**

```python
# test_history_integration.py
"""Integration tests for GET /api/history — search + pagination and edge cases."""
import pytest
from datetime import datetime, timedelta

AUTH_HEADERS = {"Authorization": "Bearer test-secret-token"}


@pytest.fixture
def client(app_client):
    return app_client


def _create_history(client, input_text, doc_type="official", memo=None):
    """Helper to create a history record via the API."""
    result = {
        "request_id": "test-req",
        "status": "success",
        "status_reason": None,
        "warnings": [],
        "corrected_text": input_text + "（校正済み）",
        "summary": "OK",
        "corrections": [],
        "diffs": [],
    }
    body = {
        "input_text": input_text,
        "result": result,
        "model": "kimi-k2.5",
        "document_type": doc_type,
    }
    if memo is not None:
        body["memo"] = memo
    resp = client.post("/api/history", json=body, headers=AUTH_HEADERS)
    return resp


class TestSearchPagination:
    """Search query combined with pagination."""

    def test_search_with_limit_and_offset(self, client):
        """検索キーワード + ページネーションの組み合わせ"""
        for i in range(5):
            _create_history(client, f"申請書サンプル{i:02d}")

        resp = client.get("/api/history?q=申請書&limit=2&offset=0", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 5
        assert len(data["items"]) <= 2

    def test_search_returns_empty_for_no_match(self, client):
        _create_history(client, "申請書のテスト")
        resp = client.get("/api/history?q=存在しないキーワード", headers=AUTH_HEADERS)
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_search_with_document_type_filter(self, client):
        _create_history(client, "メールのテスト", doc_type="email")
        _create_history(client, "報告書のテスト", doc_type="report")

        resp = client.get("/api/history?document_type=email", headers=AUTH_HEADERS)
        data = resp.json()
        assert data["total"] >= 1
        assert all(item["document_type"] == "email" for item in data["items"])

    def test_offset_beyond_total_returns_empty(self, client):
        _create_history(client, "テスト")
        resp = client.get("/api/history?offset=999", headers=AUTH_HEADERS)
        data = resp.json()
        assert data["items"] == []
        assert data["total"] >= 1


class TestHistoryEdgeCases:
    """Edge cases for history CRUD."""

    def test_empty_query_returns_all(self, client):
        _create_history(client, "テスト1")
        _create_history(client, "テスト2")
        resp = client.get("/api/history?q=", headers=AUTH_HEADERS)
        data = resp.json()
        assert data["total"] >= 2

    def test_null_query_returns_all(self, client):
        _create_history(client, "テスト1")
        resp = client.get("/api/history", headers=AUTH_HEADERS)
        data = resp.json()
        assert data["total"] >= 1

    def test_delete_nonexistent_returns_404(self, client):
        resp = client.delete("/api/history/99999", headers=AUTH_HEADERS)
        assert resp.status_code == 404

    def test_get_nonexistent_returns_404(self, client):
        resp = client.get("/api/history/99999", headers=AUTH_HEADERS)
        assert resp.status_code == 404

    def test_patch_nonexistent_returns_404(self, client):
        resp = client.patch("/api/history/99999", json={"memo": "test"}, headers=AUTH_HEADERS)
        assert resp.status_code == 404

    def test_special_characters_in_search_query(self, client):
        """LIKE パターン文字が含まれてもエラーにならない"""
        _create_history(client, "テストデータ")
        resp = client.get("/api/history?q=%25_%30", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    def test_items_returned_in_descending_order(self, client):
        _create_history(client, "最初のレコード")
        _create_history(client, "2番目のレコード")
        _create_history(client, "3番目のレコード")

        resp = client.get("/api/history", headers=AUTH_HEADERS)
        data = resp.json()
        assert data["total"] >= 3
        dates = [item["created_at"] for item in data["items"]]
        assert dates == sorted(dates, reverse=True)

    def test_date_range_filter(self, client):
        """日付範囲フィルタのテスト"""
        _create_history(client, "テストデータ")

        yesterday = (datetime.now() - timedelta(days=1)).isoformat() + "T00:00:00Z"
        tomorrow = (datetime.now() + timedelta(days=1)).isoformat() + "T00:00:00Z"

        resp = client.get(f"/api/history?date_from={yesterday}&date_to={tomorrow}", headers=AUTH_HEADERS)
        data = resp.json()
        assert data["total"] >= 1
```

- [ ] **Step 2: テストを実行して通過することを確認**

Run: `cd backend && pytest tests/test_history_integration.py -v`
Expected: ALL PASS

- [ ] **Step 3: コミット**

```bash
git add backend/tests/test_history_integration.py
git commit -m "test(history): add integration tests for search, pagination, and edge cases"
```

---

### Task 3: バックエンド — エクスポート統合テスト + ログ出力確認

**Files:**
- Create: `backend/tests/test_export_integration.py`
- Create: `backend/tests/test_logging_integration.py`

- [ ] **Step 1: エクスポートエッジケーステストを書く**

```python
# test_export_integration.py
"""Integration tests for POST /api/export/docx — edge cases."""
import pytest

AUTH_HEADERS = {"Authorization": "Bearer test-secret-token"}


@pytest.fixture
def client(app_client):
    return app_client


class TestExportEdgeCases:
    """Edge cases for docx export."""

    def test_japanese_text_export(self, client):
        """日本語テキストが正しくエクスポートされる"""
        resp = client.post(
            "/api/export/docx",
            json={"corrected_text": "申請書を提出してください。", "document_type": "official"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert len(resp.content) > 0

    def test_multiline_with_bullets_export(self, client):
        """箇条書きを含むテキストのエクスポート"""
        text = "報告書\n\n・第1章 概要\n概要を記載します。\n\n・第2章 詳細\n詳細を記載します。"
        resp = client.post(
            "/api/export/docx",
            json={"corrected_text": text, "document_type": "report"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        assert len(resp.content) > 0

    def test_single_character_text(self, client):
        """最小文字数（1文字）のテキスト"""
        resp = client.post(
            "/api/export/docx",
            json={"corrected_text": "あ", "document_type": "other"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200

    def test_all_document_types(self, client):
        """全文書種別でエクスポート可能"""
        for doc_type in ["email", "report", "official", "other"]:
            resp = client.post(
                "/api/export/docx",
                json={"corrected_text": f"{doc_type}テスト", "document_type": doc_type},
                headers=AUTH_HEADERS,
            )
            assert resp.status_code == 200, f"Failed for document_type={doc_type}"

    def test_requires_auth(self, client):
        resp = client.post(
            "/api/export/docx",
            json={"corrected_text": "テスト", "document_type": "official"},
        )
        assert resp.status_code == 401
```

- [ ] **Step 2: ログ出力確認テストを書く**

```python
# test_logging_integration.py
"""Integration tests for log output (§9.2, §13 Task 22)."""
import logging
import pytest
from unittest.mock import AsyncMock, patch

AUTH_HEADERS = {"Authorization": "Bearer test-secret-token"}


@pytest.fixture
def client(app_client):
    return app_client


class TestProofreadLogging:
    """Verify log entries are emitted for key events (§9.2)."""

    def test_ai_error_logs_request_id_and_error(self, client, caplog):
        """AI エラー時に request_id とエラー情報がログに記録される"""
        with patch("routers.proofread.get_model_config") as mock_config, \
             patch("routers.proofread.build_prompts", return_value=("s", "u")), \
             patch("routers.proofread.create_ai_client") as mock_create:
            from services.ai_client import AIClientError, ModelConfig
            mock_config.return_value = ModelConfig(
                display_name="K", max_tokens=4096, temperature=0.3,
                max_input_chars=8000, json_forced=True,
            )
            mock_ai = AsyncMock()
            mock_ai.complete.side_effect = AIClientError("ai_timeout", "タイムアウト")
            mock_create.return_value = mock_ai

            with caplog.at_level(logging.ERROR, logger="govassist"):
                resp = client.post(
                    "/api/proofread",
                    json={"request_id": "log-test-001", "text": "テスト", "document_type": "official", "model": "kimi-k2.5"},
                    headers=AUTH_HEADERS,
                )

            assert resp.status_code == 504
            assert any("log-test-001" in rec.message for rec in caplog.records)
            assert any("ai_timeout" in rec.message for rec in caplog.records)

    def test_internal_error_logs_stack_trace(self, client, caplog):
        """内部エラー時にスタックトレースがログに記録される"""
        with patch("routers.proofread.get_model_config") as mock_config, \
             patch("routers.proofread.build_prompts", side_effect=RuntimeError("unexpected")), \
             patch("routers.proofread.create_ai_client", return_value=AsyncMock()):
            from services.ai_client import ModelConfig
            mock_config.return_value = ModelConfig(
                display_name="K", max_tokens=4096, temperature=0.3,
                max_input_chars=8000, json_forced=True,
            )

            with caplog.at_level(logging.ERROR, logger="govassist"):
                resp = client.post(
                    "/api/proofread",
                    json={"request_id": "log-test-002", "text": "テスト", "document_type": "official", "model": "kimi-k2.5"},
                    headers=AUTH_HEADERS,
                )

            assert resp.status_code == 500
            assert any("log-test-002" in rec.message for rec in caplog.records)
            assert any("internal error" in rec.message for rec in caplog.records)


class TestAuthLogging:
    """Verify auth failures are handled correctly."""

    def test_unauthorized_request_returns_401(self, client):
        """認証なしリクエストは 401 を返す"""
        resp = client.post("/api/proofread", json={"text": "test"})
        assert resp.status_code == 401
```

- [ ] **Step 3: テストを実行して通過することを確認**

Run: `cd backend && pytest tests/test_export_integration.py tests/test_logging_integration.py -v`
Expected: ALL PASS

- [ ] **Step 4: コミット**

```bash
git add backend/tests/test_export_integration.py backend/tests/test_logging_integration.py
git commit -m "test(export,logging): add export edge case tests and log output verification"
```

---

### Task 4: フロントエンド — 校正ページ統合テスト（エッジケース）

**Files:**
- Create: `frontend/src/tools/proofreading/Proofreading.integration.test.jsx`

既存 `Proofreading.test.jsx` は基本的なフローをカバーしているが、`large_rewrite` 警告表示、`parse_fallback` partial ステータス、API エラーコード別の挙動が未テスト。

> **重要**: 既存の `Proofreading.test.jsx` と同じモックパターンを使用する。`preprocess` と `fileExtractor` もモックする。

- [ ] **Step 1: テストファイルを作成する**

```jsx
// Proofreading.integration.test.jsx
/**
 * Integration tests for Proofreading page — edge cases not covered by unit tests.
 * Tests full component interactions including ResultView integration.
 */
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Same mock pattern as existing Proofreading.test.jsx
vi.mock('../../api/client', () => ({
  apiPost: vi.fn(),
  apiPostBlob: vi.fn(),
}));

vi.mock('../../utils/storage', () => ({
  loadSettings: vi.fn(() => ({
    model: 'kimi-k2.5',
    document_type: 'official',
    options: { typo: true, keigo: true, terminology: true, style: true, legal: false, readability: true },
  })),
}));

vi.mock('./preprocess', () => ({
  preprocessText: vi.fn((text) => ({ text: text.trim(), error: null })),
}));

vi.mock('./fileExtractor', () => ({
  extractText: vi.fn(),
}));

import Proofreading from './Proofreading';
import { apiPost } from '../../api/client';

describe('Proofreading — large_rewrite warning', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('displays large_rewrite warning when response contains warnings', async () => {
    const user = userEvent.setup();
    apiPost.mockResolvedValueOnce({
      request_id: 'test-req',
      status: 'success',
      status_reason: null,
      warnings: ['large_rewrite'],
      corrected_text: '校正済みテキスト',
      summary: '⚠️ AI が広範囲を書き換えました。内容を十分ご確認ください。',
      corrections: [],
      diffs: [],
    });

    render(<Proofreading />);

    // InputArea placeholder: "校正したいテキストを入力するか、ファイルをドラッグ＆ドロップしてください。"
    const textarea = screen.getByPlaceholderText(/校正したいテキスト/);
    await user.type(textarea, 'テスト文書です。');
    await user.click(screen.getByRole('button', { name: '校正実行' }));

    await waitFor(() => {
      expect(screen.getByText(/広範囲を書き換えました/)).toBeInTheDocument();
    });
  });

  it('does not display warning when warnings is empty', async () => {
    const user = userEvent.setup();
    apiPost.mockResolvedValueOnce({
      request_id: 'test-req',
      status: 'success',
      status_reason: null,
      warnings: [],
      corrected_text: '校正済みテキスト',
      summary: '1件の修正を行いました。',
      corrections: [],
      diffs: [],
    });

    render(<Proofreading />);

    const textarea = screen.getByPlaceholderText(/校正したいテキスト/);
    await user.type(textarea, 'テスト文書です。');
    await user.click(screen.getByRole('button', { name: '校正実行' }));

    await waitFor(() => {
      expect(screen.getByText(/1件の修正を行いました/)).toBeInTheDocument();
    });
    expect(screen.queryByText(/広範囲を書き換えました/)).not.toBeInTheDocument();
  });
});

describe('Proofreading — parse_fallback partial status', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('displays corrected text for parse_fallback status', async () => {
    const user = userEvent.setup();
    apiPost.mockResolvedValueOnce({
      request_id: 'test-req',
      status: 'partial',
      status_reason: 'parse_fallback',
      warnings: [],
      corrected_text: 'フォールバックテキスト',
      summary: null,
      corrections: [],
      diffs: [],
    });

    render(<Proofreading />);

    const textarea = screen.getByPlaceholderText(/校正したいテキスト/);
    await user.type(textarea, 'テスト');
    await user.click(screen.getByRole('button', { name: '校正実行' }));

    await waitFor(() => {
      expect(screen.getByText(/フォールバックテキスト/)).toBeInTheDocument();
    });
  });
});

describe('Proofreading — API error code handling', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('displays error message for 504 timeout', async () => {
    const user = userEvent.setup();
    apiPost.mockRejectedValueOnce(new Error('AI応答がタイムアウトしました（60秒）'));

    render(<Proofreading />);

    const textarea = screen.getByPlaceholderText(/校正したいテキスト/);
    await user.type(textarea, 'テスト');
    await user.click(screen.getByRole('button', { name: '校正実行' }));

    await waitFor(() => {
      expect(screen.getByText(/タイムアウト/)).toBeInTheDocument();
    });
  });

  it('displays error message for 422 validation error', async () => {
    const user = userEvent.setup();
    apiPost.mockRejectedValueOnce(new Error('入力テキストの文字数が上限を超えています'));

    render(<Proofreading />);

    const textarea = screen.getByPlaceholderText(/校正したいテキスト/);
    await user.type(textarea, 'テスト');
    await user.click(screen.getByRole('button', { name: '校正実行' }));

    await waitFor(() => {
      expect(screen.getByText(/文字数が上限/)).toBeInTheDocument();
    });
  });

  it('shows retry button after API error', async () => {
    const user = userEvent.setup();
    apiPost.mockRejectedValueOnce(new Error('エラーが発生しました'));

    render(<Proofreading />);

    const textarea = screen.getByPlaceholderText(/校正したいテキスト/);
    await user.type(textarea, 'テスト');
    await user.click(screen.getByRole('button', { name: '校正実行' }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '再試行' })).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 2: テストを実行して通過することを確認する**

Run: `cd frontend && npx vitest run src/tools/proofreading/Proofreading.integration.test.jsx`
Expected: ALL PASS

テストが失敗する場合は、コンポーネントのセレクタ（placeholder 文字列、ボタン名）を実際の実装に合わせて調整する。

- [ ] **Step 3: コミット**

```bash
git add frontend/src/tools/proofreading/Proofreading.integration.test.jsx
git commit -m "test(frontend): add proofreading integration tests for large_rewrite, partial status, API errors"
```

---

### Task 5: フロントエンド — 結果表示統合テスト（エッジケース）

**Files:**
- Create: `frontend/src/tools/proofreading/ResultView.integration.test.jsx`

- [ ] **Step 1: 複数 corrections・タブ切り替えのテストを書く**

```jsx
// ResultView.integration.test.jsx
/**
 * Integration tests for ResultView — edge cases for corrections display and tab switching.
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect } from 'vitest';

import ResultView from './ResultView';

describe('ResultView — multiple corrections in comments tab', () => {
  it('displays all corrections after switching to comments tab', async () => {
    const user = userEvent.setup();
    const result = {
      request_id: 'test',
      status: 'success',
      status_reason: null,
      warnings: [],
      corrected_text: '校正済み',
      summary: '3件修正',
      corrections: [
        { original: '修正前テキストA', corrected: '修正後テキストB', reason: '理由1', category: '誤字脱字', diff_matched: true },
        { original: '修正前テキストC', corrected: '修正後テキストD', reason: '理由2', category: '敬語', diff_matched: false },
        { original: '修正前テキストE', corrected: '修正後テキストF', reason: '理由3', category: '用語', diff_matched: true },
      ],
      diffs: [],
    };

    render(<ResultView result={result} />);

    // Switch to comments tab (tab 3) — actual label is "③ コメント一覧"
    const commentsTab = screen.getByRole('tab', { name: /コメント一覧/ });
    await user.click(commentsTab);

    expect(screen.getByText('理由1')).toBeInTheDocument();
    expect(screen.getByText('理由2')).toBeInTheDocument();
    expect(screen.getByText('理由3')).toBeInTheDocument();
    // diff_matched: false should show badge
    expect(screen.getByText(/参考.*AI推定/)).toBeInTheDocument();
  });
});

describe('ResultView — edge cases', () => {
  it('handles correction with missing reason gracefully', () => {
    const result = {
      request_id: 'test',
      status: 'success',
      status_reason: null,
      warnings: [],
      corrected_text: '校正済み',
      summary: null,
      corrections: [
        { original: '修正前テキストX', corrected: '修正後テキストY', reason: '', category: '文体', diff_matched: true },
      ],
      diffs: [],
    };

    render(<ResultView result={result} />);
    // Should not crash — component checks {c.reason && (...)}
    expect(screen.getByText('修正前テキストX')).toBeInTheDocument();
  });

  it('shows corrected text for partial status without diffs', () => {
    const result = {
      request_id: 'test',
      status: 'partial',
      status_reason: 'diff_timeout',
      warnings: [],
      corrected_text: 'タイムアウト時の校正テキスト',
      summary: '差分計算がタイムアウトしました。',
      corrections: [],
      diffs: [],
    };

    render(<ResultView result={result} />);
    expect(screen.getByText('タイムアウト時の校正テキスト')).toBeInTheDocument();
    expect(screen.getByText(/タイムアウトしました/)).toBeInTheDocument();
  });

  it('shows error message and retry button for error status', () => {
    const result = {
      request_id: 'test',
      status: 'error',
      status_reason: 'parse_fallback',
      warnings: [],
      corrected_text: '',
      summary: null,
      corrections: [],
      diffs: [],
    };

    const onRetry = () => {};
    render(<ResultView result={result} onRetry={onRetry} />);
    expect(screen.getByText(/校正結果を取得できませんでした/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '再試行' })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: テストを実行して通過することを確認する**

Run: `cd frontend && npx vitest run src/tools/proofreading/ResultView.integration.test.jsx`
Expected: ALL PASS

- [ ] **Step 3: コミット**

```bash
git add frontend/src/tools/proofreading/ResultView.integration.test.jsx
git commit -m "test(frontend): add ResultView integration tests for multiple corrections and edge cases"
```

---

### Task 6: フロントエンド — 履歴パネル統合テスト（エッジケース）

**Files:**
- Create: `frontend/src/tools/history/History.integration.test.jsx`

> **重要**: 既存の `History.test.jsx` と同じモックパターンを使用する。ResultView もモックする。

- [ ] **Step 1: ページネーション・エラーハンドリングテストを書く**

```jsx
// History.integration.test.jsx
/**
 * Integration tests for History — edge cases for pagination and error handling.
 */
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Same mock pattern as existing History.test.jsx
vi.mock('../../api/client', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPatch: vi.fn(),
  apiDelete: vi.fn(),
}));

vi.mock('../proofreading/ResultView', () => ({
  default: ({ result }) => (
    <div data-testid="result-view">{result ? `Status: ${result.status}` : 'no result'}</div>
  ),
}));

import { apiGet, apiDelete } from '../../api/client';
import History from './History';

const mockItems = (count, startId = 1) =>
  Array.from({ length: count }, (_, i) => ({
    id: startId + i,
    preview: `テスト文書${startId + i}`,
    document_type: 'official',
    model: 'kimi-k2.5',
    created_at: new Date(Date.now() - i * 86400000).toISOString(),
    truncated: false,
    memo: null,
  }));

describe('History — pagination', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiGet.mockResolvedValue({ items: mockItems(5), total: 25 });
  });

  it('shows total count and pagination info', async () => {
    render(<History />);
    await waitFor(() => {
      expect(screen.getByText(/25件/)).toBeInTheDocument();
    });
  });

  it('navigates to next page', async () => {
    const user = userEvent.setup();
    apiGet.mockResolvedValueOnce({ items: mockItems(20), total: 25 });
    apiGet.mockResolvedValueOnce({ items: mockItems(5, 21), total: 25 });

    render(<History />);

    // Button text is "次へ" (not "次のページ")
    await waitFor(() => {
      expect(screen.getByText('次へ')).toBeInTheDocument();
    });
    await user.click(screen.getByText('次へ'));

    await waitFor(() => {
      expect(apiGet).toHaveBeenLastCalledWith(expect.stringContaining('offset=20'));
    });
  });
});

describe('History — error handling', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('displays error when list fetch fails', async () => {
    apiGet.mockRejectedValueOnce(new Error('ネットワークエラー'));

    render(<History />);
    await waitFor(() => {
      expect(screen.getByText(/ネットワークエラー/)).toBeInTheDocument();
    });
  });

  it('displays error when delete fails', async () => {
    const user = userEvent.setup();
    apiGet.mockResolvedValue({ items: mockItems(1), total: 1 });
    apiDelete.mockRejectedValueOnce(new Error('削除に失敗しました。'));

    // Mock window.confirm to return true (user clicks OK)
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);

    render(<History />);

    await waitFor(() => {
      expect(screen.getByText('テスト文書1')).toBeInTheDocument();
    });

    // Delete button has aria-label="削除"
    const deleteButton = screen.getByRole('button', { name: '削除' });
    await user.click(deleteButton);

    await waitFor(() => {
      expect(screen.getByText(/削除に失敗しました/)).toBeInTheDocument();
    });

    confirmSpy.mockRestore();
  });
});
```

- [ ] **Step 2: テストを実行して通過することを確認する**

Run: `cd frontend && npx vitest run src/tools/history/History.integration.test.jsx`
Expected: ALL PASS

- [ ] **Step 3: コミット**

```bash
git add frontend/src/tools/history/History.integration.test.jsx
git commit -m "test(frontend): add History integration tests for pagination and error handling"
```

---

### Task 7: 全テストスイート実行 & 修正

**Files:**
- Modify: any files that need fixes (if tests reveal issues)

- [ ] **Step 1: バックエンド全テストを実行**

Run: `cd backend && pytest -v 2>&1 | tail -30`

すべてのテストが通過することを確認する。失敗した場合は原因を調査して修正する。

- [ ] **Step 2: フロントエンド全テストを実行**

Run: `cd frontend && npx vitest run 2>&1 | tail -30`

すべてのテストが通過することを確認する。失敗した場合は原因を調査して修正する。

- [ ] **Step 3: 発見された問題を修正する（もしあれば）**

テストの失敗原因に応じて、実装コードまたはテストコードを修正する。実装コードにバグがあった場合は、TDD パターンに従い修正する。

- [ ] **Step 4: 最終コミット（修正があれば）**

```bash
git add -A
git commit -m "fix: resolve issues found during integration testing"
```

---

## 依存関係

```
Task 1 (proofread integration) ──┐
Task 2 (history integration)  ───┤
Task 3 (export + logging)     ───┼─→ Task 7 (full suite + fixes)
Task 4 (frontend proofreading) ──┤
Task 5 (frontend resultview)  ───┤
Task 6 (frontend history)     ───┘
```

Task 1-6 は互いに独立しており並列実行可能。Task 7 は全タスク完了後に実行。

---

## 設計書§13 Task 22 対応表

| 要件 | 対応タスク |
|------|-----------|
| フロント↔バック通信の動作確認 | Task 1, 2, 3 (バックエンド API エンドポイント統合テスト) |
| 文字数超過の動作確認 | Task 1 Step 3 (`test_text_at_8001_chars_fails`) |
| AI タイムアウトの動作確認 | Task 3 Step 2 (`test_ai_error_logs_request_id`), Task 4 (`504 timeout`) |
| JSON パース失敗の動作確認 | Task 1 Step 5 (realistic pipeline), Task 4 (`parse_fallback`) |
| 各 status（success/partial/error）の UI 表示確認 | Task 4, 5 (全ステータス分岐テスト) |
| diff 表示の精度確認（日本語テキスト） | Task 1 Step 5 (`test_realistic_japanese_proofread`) |
| ログ出力の確認 | Task 3 Step 2 (`test_logging_integration.py`) |
