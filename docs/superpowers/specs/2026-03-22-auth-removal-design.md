# 認証の一時無効化 — 設計書

| 項目 | 内容 |
|------|------|
| 日付 | 2026-03-22 |
| ステータス | 承認済み |
| 対象 | バックエンド・フロントエンド認証のコメントアウト化 |

## 背景

GovAssist はローカル環境（localhost）での個人利用が前提の MVP である。現在、固定 Bearer トークン認証（`APP_TOKEN`）が実装されているが、1人利用・localhost限定という前提では UX として不自然である。

将来の Web 公開も視野に入れているため、認証コードは削除せずコメントアウトで残し、いつでも再有効化できるようにする。

## 変更内容

### バックエンド

#### 1. `backend/dependencies.py`

- `verify_token()` と `get_app_token()` をコメントアウトで残す
- 各関数の docstring も含めて残す

#### 2. `backend/main.py`

- `from dependencies import verify_token, get_app_token` のインポートをコメントアウトで残す

#### 3. 全ルーター（`backend/routers/*.py`）

- `Depends(verify_token)` をコメントアウトで残す
- インポート文の `verify_token` もコメントアウトで残す

#### 4. `backend/.env.example`

- `APP_TOKEN` 行をコメントアウトで残す

#### 5. `backend/tests/test_auth.py`

- ファイルは残す
- テストクラス・テスト関数に `@pytest.mark.skip(reason="Auth disabled for localhost MVP")` を付与

#### 6. `backend/tests/conftest.py`

- `from dependencies import get_app_token` インポートをコメントアウトで残す
- `app.dependency_overrides[get_app_token]` の行をコメントアウトで残す

### フロントエンド

#### 7. `frontend/src/context/AuthContext.jsx`

- `AuthProvider` 内で `isAuthenticated` を常に `true` にするよう変更（コメントアウトで元の検証ロジックを残す）
- `login()` / `logout()` メソッドは残す（将来再有効化時に使用）
- token 検証の `apiGet('/api/models')` 呼び出しをコメントアウトで残す

#### 8. `frontend/src/components/ProtectedRoute.jsx`

- 常に `children` をレンダリングするよう変更（コメントアウトで元の認証チェックを残す）

#### 9. `frontend/src/components/LoginForm.jsx`

- コンポーネントは残す（ファイルごと変更なし）
- `App.jsx` 側で `/login` ルートを無効化するため実質的に到達不能になる

#### 10. `frontend/src/App.jsx`

- `/login` ルートをコメントアウトで残す
- `ProtectedRoute` でラップしている部分をコメントアウトで残し、直接 `children` をレンダリングするよう変更
- `App.test.jsx` も `App.jsx` の構造変更に合わせて更新（`ProtectedRoute` ラップ除去、`/login` ルート除去）

#### 11. `frontend/src/api/client.js`

- `request()` 関数内の `Authorization` ヘッダー付与ロジックをコメントアウトで残す
- `request()` 関数内の 401 時の `removeToken()` / `auth:logout` イベント送信をコメントアウトで残す
- `apiPostBlob()` 関数内の同様の認証ロジックもコメントアウトで残す

#### 12. `frontend/src/utils/token.js`

- ファイルは残す（変更なし）

### テスト

#### 13. フロントエンドテスト（以下のファイルに `describe.skip` を追加）

- `frontend/src/context/AuthContext.test.jsx`
- `frontend/src/components/LoginForm.test.jsx`
- `frontend/src/components/ProtectedRoute.test.jsx`
- `frontend/src/utils/token.test.js`
- `frontend/src/api/client.test.js` — 認証関連テスト（Authorization ヘッダー、401 処理）のみスキップ

### 設計書

#### 15. `CLAUDE.md`

- 認証関連の記述（`verify_token()` dependency、`APP_TOKEN`、`Authorization: Bearer`）に「MVP では無効化」の注記を追加

### 設計書

#### 16. `docs/design.md`

- §5.5 エラーレスポンス: `401 | unauthorized` 行に「（認証再有効化時に使用）」注記を追加
- §8.2: 「MVP では認証なし（localhost限定）。将来的な再有効化手順は `docs/superpowers/specs/2026-03-22-auth-removal-design.md` を参照。」に更新
- §10: 認証関連の記述を「MVP では認証なし」に更新

## 残すもの（変更なし）

- Origin チェックミドルウェア（`OriginCheckMiddleware`）
- XSS 対策ルール（dangerouslySetInnerHTML 禁止）
- 起動時 localhost 警告モーダル（`WarningModal.jsx`）
- AI Engine API キー管理（`.env` の `AI_ENGINE_API_KEY`）
- CORS 設定（localhost 限定、`allow_headers` の `Authorization` 含む）
- `Header.jsx` のモデル取得ロジック

## 変更しないこと

- API エンドポイントの設計・レスポンス形式
- ログ出力
- データベーススキーマ
- `frontend/src/main.jsx`（`AuthProvider` ラップは維持）

## 再有効化手順（将来）

### バックエンド

1. `dependencies.py` のコメントアウトを解除
2. `main.py` の `verify_token, get_app_token` インポートを解除
3. 各ルーターの `Depends(verify_token)` のコメントアウトを解除
4. `.env.example` の `APP_TOKEN` を有効化し、`.env` に実際のトークンを設定
5. `test_auth.py` の `@pytest.mark.skip` を削除
6. `conftest.py` のインポートと `dependency_overrides` を有効化

### フロントエンド

7. `AuthContext.jsx` の元の検証ロジックを再有効化
8. `ProtectedRoute.jsx` の元の認証チェックを再有効化
9. `App.jsx` の `/login` ルートと `ProtectedRoute` ラップを再有効化
10. `client.js` の Authorization ヘッダーと 401 処理を再有効化
11. フロントエンドテストの `describe.skip` を削除
