# GovAssist

自治体職員向けのAI文書校正Webアプリケーション。メール、報告書、公文書などの日本語文書をAIで校正・推敲します。

**ローカル環境専用** — 外部デプロイを想定していません。

## 特徴

- **AI校正** — SAKURA Internet AI Engine (OpenAI互換API) による日本語文書校正。デフォルトモデル: Kimi K2.5
- **3タブ表示** — ハイライト表示・比較表示・指摘コメントの3つのビューで校正結果を確認
- **ファイル入力** — .docx / PDF ファイルのドラッグ&ドロップ対応（mammoth.js / pdf.js でクライアント側パース）
- **文書エクスポート** — 校正結果を .docx 形式でダウンロード（箇条書き・番号付きリスト自動検出）
- **履歴管理** — SQLite + FTS5 (ngram) による全文検索付き履歴保存。自動クリーンアップ機能付き
- **耐堅牢なAI応答処理** — 3回リトライ + フォールバック戦略。AI出力を一切信用せずサーバー側で検証

## 技術スタック

| レイヤー | 技術 |
|----------|------|
| フロントエンド | React 18 / Vite, プレーンCSS |
| バックエンド | Python 3.12+ / FastAPI / Uvicorn |
| AI | SAKURA Internet AI Engine (OpenAI互換API) |
| データベース | SQLite + FTS5 (ngram) / SQLAlchemy / Alembic |
| ファイルパース | mammoth.js (.docx), pdf.js (PDF) — クライアント側 |
| 差分計算 | diff-match-patch (Python) — サーバー側 |
| Docx出力 | python-docx — サーバー側 |

## セットアップ

### 前提条件

- Python 3.12+
- Node.js 18+
- SAKURA Internet AI Engine APIキー

### バックエンド

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# .env を編集して APIキーとトークンを設定
alembic upgrade head
```

### フロントエンド

```bash
cd frontend
npm install
```

## 開発サーバー起動

```bash
./dev.sh
```

tmuxセッション `gov-assist` が立ち上がり、左右分割で以下が起動します:

- 左ペイン: Backend（uvicorn --reload、port 8000）
- 右ペイン: Frontend（Vite、port 5173）

ブラウザで `http://localhost:5173` にアクセスしてください。

| 操作 | キー/コマンド |
|------|-------------|
| デタッチ（ターミナルに戻る） | `Ctrl+B`, `D` |
| 再接続 | `tmux attach -t gov-assist` |
| サーバーを完全に終了 | `tmux kill-session -t gov-assist` |

### 環境変数

バックエンドの `.env` で設定:

| 変数 | 説明 | デフォルト |
|------|------|-----------|
| `AI_ENGINE_API_KEY` | SAKURA AI Engine APIキー | (必須) |
| `AI_ENGINE_BASE_URL` | AI Engine API endpoint | `https://api.ai.sakura.ad.jp/v1` |
| `APP_TOKEN` | API認証トークン | (必須) |
| `CORS_ORIGINS` | 許可するオリジン (カンマ区切り) | `http://localhost:5173` |
| `DATABASE_URL` | データベースURL | `sqlite:///data/govassist.db` |

## プロジェクト構成

```
gov-assist/
├── backend/
│   ├── main.py              # アプリケーションファクトリ
│   ├── database.py          # DBエンジン/セッション, FTS5初期化
│   ├── models.py            # ORMモデル (History, Settings)
│   ├── schemas.py           # Pydantic リクエスト/レスポンスモデル
│   ├── dependencies.py      # 認証依存関係
│   ├── routers/             # APIルートハンドラ
│   │   ├── proofread.py     #   校正エンドポイント
│   │   ├── history.py       #   履歴CRUD
│   │   ├── export.py        #   .docxエクスポート
│   │   ├── models_router.py #   AIモデル一覧
│   │   └── settings.py      #   サーバー設定
│   ├── services/            # ビジネスロジック
│   │   ├── ai_client.py     #   AI APIクライアント
│   │   ├── prompt_builder.py#   プロンプト構築
│   │   ├── response_parser.py#  AI応答パーサ (リトライ+フォールバック)
│   │   ├── diff_service.py  #   差分計算パイプライン
│   │   ├── history_service.py#  履歴サービス (自動クリーンアップ)
│   │   └── docx_exporter.py #   .docx生成
│   ├── migrations/          # Alembicマイグレーション
│   └── tests/               # テストスイート
├── frontend/
│   └── src/
│       ├── main.jsx         # エントリーポイント
│       ├── App.jsx          # ルーティング
│       ├── api/client.js    # HTTPクライアント
│       ├── components/      # 共通コンポーネント
│       ├── tools/           # 機能モジュール
│       │   ├── proofreading/#   校正ツール
│       │   ├── history/     #   履歴ツール
│       │   └── settings/    #   設定ツール
│       ├── context/         # React Context
│       ├── utils/           # ユーティリティ
│       └── css/             # スタイルシート
└── docs/
    └── design.md            # 設計仕様書 (v1.8.0)
```

## API エンドポイント

| メソッド | パス | 説明 |
|----------|------|------|
| GET | `/api/health` | ヘルスチェック（認証不要） |
| POST | `/api/proofread` | AI文書校正 |
| GET | `/api/models` | 利用可能なAIモデル一覧 |
| GET | `/api/history` | 履歴一覧（検索・フィルタ・ページネーション） |
| POST | `/api/history` | 履歴作成 |
| PATCH | `/api/history/{id}` | 履歴更新（メモ） |
| DELETE | `/api/history/{id}` | 履歴削除 |
| DELETE | `/api/history` | 全履歴削除 |
| POST | `/api/export/docx` | .docxエクスポート |
| GET | `/api/settings` | サーバー設定取得 |
| PUT | `/api/settings` | サーバー設定更新 |

認証: `Authorization: Bearer {token}` ヘッダー

## テスト

```bash
# バックエンド
cd backend
pytest                  # 全テスト実行
pytest -x               # 最初の失敗で停止
pytest tests/test_proofread.py  # 特定ファイルのみ

# フロントエンド
cd frontend
npm test                # 全テスト実行
npm run test:watch      # ウォッチモード
```

## 限制事項

| 項目 | 制限 |
|------|------|
| 入力テキスト | 8,000文字/回 |
| 履歴保存数 | デフォルト50件（1–200件 設定可能） |
| DB容量上限 | 20MB（自動クリーンアップ） |
| 結果JSON | 100KB/レコード（超過時はフラグ付きで切り詰め） |

## ライセンス

個人利用のみ。
