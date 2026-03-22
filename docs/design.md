# アプリ設計書
## 自治体職員向け　事務効率化ツール「GovAssist（仮称）」

| 項目 | 内容 |
|------|------|
| バージョン | v1.8.0 (MVP) |
| 作成日 | 2026年3月 |
| 対象ユーザー | 一般事務 地方自治体職員（個人利用） |
| ステータス | MVP 設計・開発フェーズ |

---

## 1. プロダクト概要

### 1.1 目的

本アプリ「GovAssist」は、地方自治体の一般事務職員が日常業務で作成・確認する各種文書（メール、報告書、公文書など）を、AIを活用して効率よく校正・改善するための個人利用 Web アプリケーションである。

MVP では AI 文書校正機能を中心に構築し、サイドメニューによるツール拡張アーキテクチャを採用することで、将来的な機能追加（PDF 加工、文書要約、AI チャットなど）をスムーズに行えるよう設計する。

### 1.2 対象ユーザー

- 地方自治体の一般事務職員（個人利用）
- 公文書・報告書・メールなどを日常的に作成するユーザー
- IT リテラシーは標準的なオフィスワーカーレベルを想定

### 1.3 設計方針

- フロントエンドは **React（Vite）**、バックエンドは **Python（FastAPI）** で構築する
- MVP はシンプルな構成・最小限のスタイリング（素の CSS）で構築する（Tailwind 不使用）
- サイドメニュー型のツールハブ構造とし、機能をモジュールとして追加できる拡張性を持たせる
- AI Engine は「さくらの AI Engine」を使用し、デフォルトモデルは **Kimi K2.5** とする
- API キーはバックエンドで管理し、フロントエンドには露出させない
- **AI の出力は信頼しすぎない。** JSON パース・バリデーション・フォールバックを必ずバックエンドで実施する
- **フロントエンドで corrected_text を再構築しない。** ハイライト・比較表示に diffs を使い、正解テキストは `corrected_text` をそのまま使う
- **フロントエンドは diffs を reduce 的に逐次レンダリングする。** `start` は使わず配列の順序のみに依存して処理し、順序崩れによるズレを防ぐ
- **localStorage はキャッシュ扱いとする。** スキーマバージョン（`version`）を持たせ、将来のサーバー移行・マイグレーションに備える
- **UI の表示ロジックは diff ベースに統一する。** AI の corrections は「参考情報」として扱い、ハイライト・比較表示の根拠には使用しない
- **本アプリはローカル環境での個人利用を前提とする。外部ネットワークへの公開は想定しない。**

---

## 2. システム構成

### 2.1 動作環境

| 項目 | 内容 |
|------|------|
| プラットフォーム | Web ブラウザ（PC）、ローカル環境限定 |
| 推奨ブラウザ | Google Chrome 最新版 / Microsoft Edge 最新版 |
| 推奨解像度 | 1280 × 720 以上 |
| ネットワーク前提 | ローカル環境のみ（`localhost`）。外部公開不可。 |
| HTTPS | `localhost` 運用時は HTTP で許容する。外部公開する場合は HTTPS 必須（その場合はセキュリティ設計を別途見直すこと）。 |
| モバイル対応 | MVP では対象外（将来対応可） |

### 2.2 技術スタック

| レイヤー | 技術 | 備考 |
|----------|------|------|
| フロントエンド | React 18 / Vite | Tailwind 不使用。素の CSS で実装。 |
| バックエンド | Python 3.12 / FastAPI | Uvicorn で起動。AI 呼び出し・差分計算・ファイル生成を担当。 |
| フロント↔バック通信 | REST API（JSON） | fetch API でリクエスト。全リクエストに `X-Request-ID` を付与。 |
| AI Engine | さくらの AI Engine | バックエンド経由で呼び出し（キーをフロントに露出させない） |
| デフォルトモデル | Kimi K2.5 | 設定画面からモデル切替可能 |
| テキスト抽出（入力） | mammoth.js（.docx）/ pdf.js（PDF） | クライアントサイドで抽出後、前処理してバックエンドに送信 |
| 差分計算 | diff-match-patch（Python） | バックエンドで修正前後の差分を生成。UI 表示の唯一の根拠。 |
| AI レスポンス検証 | Pydantic | スキーマバリデーション・フォールバック処理 |
| ファイル出力 | python-docx（バックエンド） | 校正済みテキストをプレーンテキストベースで .docx 生成 |
| 設定の永続化 | localStorage（`version: 1` 付き） | モデル選択・校正オプションの初期値を保存。バージョンフィールドで将来のマイグレーションに対応。 |
| 履歴の永続化 | SQLite（バックエンド）＋ FTS5（ngram） | SQLAlchemy 経由。全文検索は FTS5（ngram トークナイザ）前提のテーブル設計。将来的に PostgreSQL へ移行可能。 |
| DB マイグレーション | Alembic | スキーマ変更の管理 |
| ログ | Python logging（RotatingFileHandler） | エラーログ・API 失敗ログを記録 |
| CORS オリジン | `.env`（`CORS_ORIGINS`） | Vite ポート変更に対応するため環境変数化 |

### 2.3 アーキテクチャ概要

シングルページアプリケーション（React）として構成し、左サイドメニューでツールを選択し右ペインにコンテンツが表示されるレイアウトを採用する。フロントエンドからの AI 呼び出しはすべて FastAPI バックエンドを経由する。

**処理の流れ（校正）**

```
フロントエンド
  1. ファイル or テキスト入力
  2. クライアントでテキスト抽出（mammoth.js / pdf.js）
  3. 前処理（正規化・文字数チェック）
  4. X-Request-ID を生成し POST /api/proofread へ送信

バックエンド
  5. 入力文字数チェック（8,000文字超過はエラー返却）
  6. プロンプト生成（粒度制約・書き換え禁止ルールを含む）
  7. さくらの AI Engine 呼び出し
  8. AI レスポンスの前処理（コードブロック除去・トリム）
  9. JSON パース試行（失敗時はリトライ → fallback）
 10. Pydantic によるスキーマバリデーション
 11. diff-match-patch で入力テキストと corrected_text の差分を計算（タイムアウト 5 秒）
 12. diff 後処理：連続する同種 diff ブロックをマージし、過剰分割を抑制（日本語 1 文字単位分割対策）
 13. corrections の各エントリを diff 結果に動的近傍マッチで紐付け（reason 付与のみに使用）
 14. request_id を付与して校正結果 JSON を返却

フロントエンド
 15. **ファイル抽出後は「抽出結果プレビュー」を表示し、ユーザーが確認してから送信する**（そのまま自動送信しない）
 16. diffs を reduce 的に逐次レンダリング（インデックスを持たずシーケンス順に処理）
 17. 正解テキストの表示・コピー・ダウンロードには `corrected_text` をそのまま使う（再構築しない）
 18. corrections の reason を近傍マッチした diff ブロックにツールチップとして付随表示
 19. `diff_matched: false` の corrections は「参考（AI推定）」ラベル付きで③タブに表示
 20. `status_reason` に応じたメッセージを表示。`large_rewrite` 警告がある場合は目立つ位置に表示
 21. UIに「表示は差分ベース／コメントはAI推定」である旨を常時表示
```

| コンポーネント | 役割 |
|----------------|------|
| App Shell | 全体レイアウト管理・ルーティング |
| SideMenu | ツール一覧表示・ページ切替 |
| ProofreadingTool | AI 文書校正（MVP コア機能） |
| SettingsPanel | モデル選択・校正オプション設定 |
| HistoryPanel | 校正履歴の一覧・再閲覧・検索 |
| （拡張）SummaryTool | 文書要約・AI 翻訳（将来追加） |
| （拡張）PdfTool | PDF 切り出し・結合・変換（将来追加） |
| （拡張）ChatTool | アイデア出し・AI チャット（将来追加） |

---

## 3. 画面設計

### 3.1 全体レイアウト

- **ヘッダー**：アプリ名・設定ボタン・モデル切替セレクタ
- **左サイドメニュー**（幅 200px 固定）：ツール選択リスト
- **メインコンテンツエリア**：選択したツールの UI

### 3.2 サイドメニュー構成

| No. | メニュー名 | フェーズ | 備考 |
|-----|-----------|----------|------|
| 1 | 📝 AI 文書校正 | **MVP** | コア機能 |
| 2 | 📄 文書要約・翻訳 | Phase 2 | 将来追加 |
| 3 | 🗂 PDF 加工 | Phase 2 | 将来追加 |
| 4 | 💬 AI チャット | Phase 3 | 将来追加 |
| ⚙ | 設定 | **MVP** | フッター固定 |

### 3.3 AI 文書校正画面

#### 3.3.1 入力エリア

- テキスト直接入力・貼り付け用テキストエリア（最低 10 行表示）
- ファイルアップロードボタン：`.docx`・`.pdf` に対応
- ドラッグ＆ドロップ対応エリアとして実装
- 文書種別選択セレクタ（メール / 報告書 / 公文書 / その他）
- **入力文字数カウンター表示**（上限 8,000 文字。超過時は校正ボタンを無効化しエラーメッセージ表示）

> **⚠️ セキュリティ警告**（入力エリア上部に常時表示）
> 本ツールはテキストを外部 AI サービス（さくらの AI Engine）に送信します。
> 個人情報・機密情報を含む文書の入力はお控えください。

#### 3.3.2 前処理ルール（クライアントサイド）

ファイルから抽出したテキストは、バックエンドへ送信する前に以下の前処理を行う。

| 処理 | 内容 |
|------|------|
| 連続改行の正規化 | 3 行以上の連続改行を 2 行に圧縮 |
| 行頭・行末の空白トリム | 各行の先頭・末尾スペース・タブを除去 |
| ページ区切りの除去 | PDF 抽出時のページ境界文字列（`\f` など）を改行に変換 |
| NULL 文字除去 | 制御文字（`\x00`〜`\x08`、`\x0b`、`\x0c`、`\x0e`〜`\x1f`）を除去 |
| 文字数チェック | 前処理後に 8,000 文字を超える場合はエラー表示し送信しない |

> **文字数上限の根拠**
> Kimi K2.5 のコンテキスト上限に対し、システムプロンプト・JSON 構造・レスポンス分の余裕を確保するため、入力テキストの上限を 8,000 文字とする。日本語はトークン換算で文字数より多くなる傾向があるため、文字数ベースで保守的に設定する。モデル変更時はモデル設定テーブル（4.2）の `max_input_chars` を参照すること。

#### 3.3.3 校正オプション

校正実行前に以下のオプションを ON/OFF できるチェックボックスを設ける。

- [ ] 誤字・脱字・変換ミスの検出
- [ ] 敬語・丁寧語の適切さチェック
- [ ] 公文書用語・表現への統一（例：「ください」→「くださいますよう」）
- [ ] 文体の統一（です・ます調 / である調）
- [ ] 法令・条例用語の確認
- [ ] 文章の読みやすさ・論理構成の改善提案

#### 3.3.4 校正結果表示

**UI の表示ロジックは diff ベースに統一する。** AI の `corrections` は reason テキストを diff ブロックに添付するためだけに使用し、ハイライト位置・比較表示の根拠には使用しない。

**diff の表示仕様**

| 項目 | 仕様 |
|------|------|
| 差分の粒度 | diff-match-patch で計算後、バックエンドで後処理（連続同種ブロックのマージ＋短小ブロック吸収）。日本語 1 文字単位の過剰分割を防ぐ。 |
| `start` の定義 | 元テキスト（入力テキスト）の文字位置を基準とする。**フロントのレンダリングには使用しない（デバッグ・ログ用途のみ）**。`insert` の `start` は「元テキストのこの位置の直後に挿入」を意味し `position: "after"` を付与。 |
| **diffs の順序正規化（バックエンド責務）** | diff-match-patch はペア順序を保証しないため、バックエンドで明示的に正規化する：`[delete A][equal X][insert B]` → `[delete A][insert B][equal X]` に並べ替える。delete → insert を必ずペアで連続させ、同一 `start` の insert は出現順序を固定する。 |
| **フロントのレンダリング方針** | diffs 配列を**順序のみに依存**して先頭から reduce 的に処理する。`start` 座標は参照しない。各ブロックを「現在の出力状態」に順番通り適用していく。同一 `start` に複数の insert がある場合は配列の出現順を信頼する。 |
| **フロントの再構築禁止** | フロントエンドは `diffs` からテキストを再構築しない。ハイライト・比較表示には `diffs` を使い、コピー・ダウンロード・③タブの正解テキストには `corrected_text` をそのまま使う。 |
| 削除箇所の色 | 赤系背景（`#ffcccc`）+ 打ち消し線 |
| 追加箇所の色 | 緑系背景（`#ccffcc`） |
| 変更なし箇所 | 背景なし（通常テキスト） |
| reason の表示 | 近傍マッチした diff ブロックにツールチップとして添付。マッチしない場合は非表示（③タブには「参考（AI推定）」ラベル付きで表示）。 |
| **UI 上の明示** | 結果エリア上部に「表示は差分ベースです。コメントは AI 推定であり正確でない場合があります。」と常時表示する。 |

**3 タブ構成**

| タブ名 | 内容 |
|--------|------|
| ① ハイライト表示 | 元テキストを表示し、diff の削除・追加箇所を色付きハイライトで示す。マウスオーバーで近傍マッチした reason をポップアップ表示。 |
| ② 比較表示 | 左列に修正前・右列に修正後を並べた文字単位 diff 形式で表示。スクロール同期あり。 |
| ③ コメント一覧 | corrections の各エントリ（original / corrected / reason / category）を番号付きリストで表示。`diff_matched: false` のものには「参考（AI推定）」ラベルを付けて信頼性を明示する。 |

**status による UI 表示の分岐**

| status | status_reason | UI の挙動 |
|--------|--------------|-----------|
| `success` | null | 3 タブすべて表示。diff ベースのハイライト・比較が有効。`warnings` に `large_rewrite` がある場合は結果上部に「⚠️ AI が広範囲を書き換えました。内容を十分ご確認ください。」を目立つ形で表示。 |
| `partial` | `diff_timeout` | 行単位 diff にフォールバックした場合は①②③タブを通常通り表示（精度は低下するが「どこが変わったか」は把握できる）。行単位 diff も失敗した場合は③タブのみ表示し `corrected_text` を目立つ位置に表示。メッセージ：「差分計算がタイムアウトしました。行単位での差分を表示しています。」または「差分計算に失敗しました。校正済みテキストのみ表示します。」 |
| `partial` | `parse_fallback` | ③タブのみ表示。`corrected_text` を常時目立つ位置に表示。メッセージ：「AI の応答形式が不完全でした。取得できたテキストのみ表示します。」 |
| `error` | `parse_fallback` | タブ表示なし。「校正結果を取得できませんでした。」を表示。「再試行」ボタンを提供。 |

#### 3.3.5 処理中状態の仕様

| 状態 | UI 表現 |
|------|---------|
| テキスト抽出中 | 「ファイルを読み込んでいます...」+ スピナー |
| AI 校正中 | 「AI が校正しています...」+ スピナー（校正ボタン・入力エリアを無効化） |
| タイムアウト（60秒） | エラーメッセージ表示 + 「再試行」ボタン |
| API エラー | エラーコードに対応したメッセージを表示 + 「再試行」ボタン |

#### 3.3.6 アクションボタン

- 「**校正実行**」ボタン：AI API を呼び出し結果を表示（処理中は無効化）
- 「**クリア**」ボタン：入力・結果をリセット
- 「**校正済みテキストをコピー**」ボタン：クリップボードにコピー
- 「**Word でダウンロード (.docx)**」ボタン：バックエンドで生成した .docx をダウンロード
- 「**履歴に保存**」ボタン：校正結果をバックエンド経由で SQLite に保存

### 3.4 設定画面

設定画面はサーバー設定（`/api/settings` 経由）とクライアント設定（localStorage）を明確に分離する。

localStorage には以下の形式でスキーマバージョンを付与し、将来のサーバー移行・マイグレーションに備える。

```json
{
  "version": 1,
  "model": "kimi-k2.5",
  "document_type": "official",
  "options": { "typo": true, "keigo": true, ... }
}
```

> バージョンが変わった場合（例：`version: 2`）は、起動時に可能な限りマイグレーション（既知のフィールドのみ引き継ぎ）を試みる。マイグレーションできないフィールドがある場合のみデフォルト値で補完する。マイグレーション自体が失敗した場合のみ全項目をデフォルトにリセットする。

| 設定項目 | 保存先 | 詳細 |
|----------|--------|------|
| API キー | `.env`（変更不可） | バックエンドで管理。設定画面には表示・変更欄を設けない。 |
| モデル選択 | localStorage（キャッシュ、`version: 1`） | ドロップダウンで選択。選択肢はモデル設定テーブルから取得。将来的にはサーバー設定に移行予定。 |
| デフォルト文書種別 | localStorage（キャッシュ、`version: 1`） | 起動時の文書種別初期値。将来的にはサーバー設定に移行予定。 |
| デフォルト校正オプション | localStorage（キャッシュ、`version: 1`） | 起動時にチェックされている校正項目の初期設定。将来的にはサーバー設定に移行予定。 |
| 履歴の保存件数上限 | `/api/settings`（サーバー） | デフォルト 50 件（1〜200 件）。サーバー側 DB で管理。 |

---

## 4. AI 校正機能 詳細仕様

### 4.1 AI Engine 接続仕様

| 項目 | 仕様 |
|------|------|
| AI Engine | さくらの AI Engine |
| 呼び出し元 | FastAPI バックエンド（フロントエンドから直接呼び出しは行わない） |
| エンドポイント | さくらの AI Engine 提供の API エンドポイント（OpenAI 互換 REST API） |
| 認証方式 | Bearer Token（API キー）。`.env` ファイルで管理し、環境変数として参照。 |
| デフォルトモデル | Kimi K2.5 |
| 切替可能モデル | モデル設定テーブル（4.2）に登録されたモデルのみ |
| タイムアウト | 60 秒（超過時は HTTP 504 を返却） |
| リトライ | JSON パース失敗時は最大 2 回リトライ（計 3 回）。成功次第終了。全失敗時は `status: "partial"` または `status: "error"` で返却。 |

### 4.2 モデル設定テーブル

モデルごとの挙動差異を吸収するため、バックエンドにモデル設定を定義する。フロントのドロップダウンはこのテーブルから動的に生成する。

| モデル ID | 表示名 | max_tokens | temperature | max_input_chars | JSON 強制対応 | 備考 |
|-----------|--------|-----------|-------------|-----------------|--------------|------|
| `kimi-k2.5` | Kimi K2.5 | 4096 | 0.3 | 8000 | あり | デフォルト |
| （追加時に定義） | - | - | - | - | - | - |

> モデルを追加する際は、このテーブルに全フィールドを確認・記入してから登録すること。`max_input_chars` はモデルのコンテキスト上限から逆算し、余裕をもって設定すること。
>
> `temperature` は現在モデル単位で固定しているが、将来的に校正オプション（例：「論理構成の改善」は高め）ごとに変えたくなる可能性がある。その場合はモデル設定テーブルに `option_temperature_overrides` フィールドを追加して対応する。

### 4.3 プロンプト設計

#### システムプロンプト（固定）

```
あなたは日本の地方自治体の公文書・業務文書を専門とする文章校正アシスタントです。
以下のルールを厳守してください。

【出力ルール】
- 必ず以下の JSON 形式のみで応答すること。JSON 以外のテキスト・説明・コードブロックは一切含めないこと。
- JSON のキー名・構造を変えないこと。

【校正ルール】
- 必要最小限の修正のみ行うこと。原文の表現・構成を大幅に書き換えることを禁止する。
- 1件の correction は1箇所の最小変更単位とすること（文字〜句単位）。文単位・段落単位の一括書き換えは禁止。
- original / corrected フィールドは各 50 文字以内とすること。
- 原文を尊重し、意味の変わる書き換えは行わないこと。
```

#### ユーザープロンプト（動的生成）

```
文書種別：{選択した文書種別}
チェック項目：{選択した校正オプションのリスト}
入力文書：
{前処理済みテキスト}

以下の JSON 形式のみで返答してください：
{
  "corrected_text": "校正済み全文（原文からの最小変更のみ）",
  "summary": "校正のサマリー（修正件数・主要な指摘）",
  "corrections": [
    {
      "original": "修正前テキスト（原文から抜粋、50文字以内）",
      "corrected": "修正後テキスト（50文字以内）",
      "reason": "修正理由",
      "category": "誤字脱字 | 敬語 | 用語 | 文体 | 法令 | 読みやすさ"
    }
  ]
}
```

> `position` フィールドはプロンプトに含めない。位置情報はバックエンドの diff 処理で生成する。

### 4.4 AI レスポンス処理フロー（バックエンド）

```
1. AI からレスポンス受信
2. レスポンステキストの前処理
   - マークダウンコードブロック（```json ... ``` 等）の除去
   - 先頭・末尾の余分なテキストのトリム
3. JSON パース試行
   - 成功 → 4 へ
   - 失敗（1回目）→ 同じプロンプトで再試行
   - 失敗（2回目）→ 以下の再プロンプトで再試行（プロンプト内容を固定する）：
     ```
     あなたの前回の出力はJSONとして解析できませんでした。
     以下のJSONを正しいJSON形式に修正して出力してください。
     JSON以外のテキスト・説明・コードブロック記法は一切含めないでください。

     修正対象：
     {前回のレスポンス全文}
     ```
   - 失敗（3回目）→ fallback 抽出へ（下記）
4. Pydantic スキーマバリデーション
   - 成功 → 5 へ
   - フィールド不足 → デフォルト値補完して続行（summary: null、corrections: []）
   - **corrections の各エントリがスキーマ違反（例：original が 50 文字超・必須フィールド欠損）の場合、そのエントリのみ除外する。全エントリが除外された場合は corrections: [] として続行する（summary は保持）。corrections が壊れていても処理を止めない。**
5. diff-match-patch で入力テキストと corrected_text の差分を計算
   - タイムアウト：5 秒。超過時は **行単位 diff にフォールバックする**（文字単位 diff より大幅に高速）。行単位 diff でも 1 秒以内に完了しない場合のみ `diffs: []`・`status: "partial"`・`status_reason: "diff_timeout"` で返却する。
6. diff 後処理 ① 連続同種ブロックのマージ
   - 例：[delete("く"), delete("だ")] → [delete("くだ")]
   - insert/delete の対をひとまとまりの変更ブロックとして扱う
7. diff 後処理 ② 短小ブロックの吸収（日本語ノイズ除去）
   - **`enable_diff_compaction: true`（デフォルト）の場合のみ実行する**。MVP から ON/OFF フラグを用意し、挙動の切り替えを可能にする。
   - **2 文字未満**の equal ブロックは前後の変更ブロックとマージする（助詞＋動詞の一部修正が消えるリスクを軽減するため 3 文字から 2 文字に緩和済み）
   - 1 文字の孤立した delete/insert は隣接ブロックに統合する
   - **副作用**：「てにをは」レベル・助詞＋動詞の一部修正がまれに diff 上で見えなくなる場合がある。corrections との照合精度も若干低下するが UI 崩れは起きない。圧縮前の diff ブロック数は INFO ログに残す。
8. diffs の適用順序の正規化（アルゴリズム固定）
   以下のルールを順番に適用する：
   ```
   ルール1: 連続する delete ブロック群をひとつにまとめる
   ルール2: その直後に連続する insert ブロック群があれば同一変更として扱い、delete → insert の順で並べる
   ルール3: equal を跨ぐ場合は別の変更ブロックとして扱う（equal 跨ぎ結合禁止）
   ルール4: 同一 start の insert が複数ある場合は配列の出現順を固定する
   ```
   **「equal 跨ぎ禁止」が最重要ルール**：`[delete A][equal X][insert B]` の X が 2 文字以上の場合は A と B を別変更として扱う。X が 1 文字以下の場合のみ短小ブロック吸収（後処理②）の対象として結合を許容する。
9. corrections の各エントリを diff ブロックに動的近傍マッチで紐付け
   - original の長さが 4 文字未満の場合はマッチしない（誤爆防止）
   - マッチ幅：min(20, original.length × 2) 文字
   - original の完全一致位置を検索し、その位置が diff ブロック範囲内に収まればマッチ
   - 同語句が複数ある場合は diff ブロックに最も近いものを採用（最長一致優先）
   - **1 diff ブロックに紐づける reason は最大 1 件**（同一 diff ブロックに複数 corrections がマッチした場合は最長一致のものを採用し、残りは diff_matched: false として③タブに表示）
   - **1 correction は消費型（1 回のみ使用）**：一度マッチした correction は他の diff ブロックには紐づけない
   - **4文字未満の corrections はすべて diff_matched: false として扱い、③タブのみに表示する**
10. 大幅書き換え検知
    - **変更文字数 = delete ブロックの文字数合計 + insert ブロックの文字数合計**（equal は除外）
    - 変更文字数 ÷ 入力文字数 > 0.3（30%超）かつ **最大連続変更ブロック長 ÷ 入力文字数 > 0.3** の両方を満たす場合のみ「大幅書き換え」と判定する（改行正規化・全角半角統一など細かい修正が積み上がるケースの誤検知を防ぐ）
    - 該当時は `warnings: ["large_rewrite"]` を付与し summary に「AI が広範囲を書き換えました。内容を十分ご確認ください。」を追記
11. request_id を付与して返却

fallback 抽出（ステップ3 全失敗時）
  1. 正規表現 `"corrected_text"\s*:\s*"(.*?)"` でフィールドを抽出 → 成功なら status: "partial"
  2. JSON 構造を除いた平文テキスト部分を表示 → 成功なら status: "partial"
  3. 上記すべて失敗 → corrected_text: ""、status: "error"
```

### 4.5 diff と corrections の対応付け戦略

**基本方針：UI は diff ベースに統一し、corrections は reason 付与の補助情報とする（案A）**

| 役割 | 情報源 | 用途 |
|------|--------|------|
| ハイライト表示 | diff-match-patch の差分 | ①②タブの表示根拠 |
| 比較表示 | diff-match-patch の差分 | ①②タブの表示根拠 |
| 修正理由（reason） | AI の corrections | diff ブロックに近傍マッチで添付（③タブ・ツールチップ） |
| コメント一覧 | AI の corrections | ③タブに全件表示（diff マッチ有無を問わない） |

**近傍マッチの定義**

1. **ガード条件**：`original` の長さが 4 文字未満の場合はマッチしない（「です」「ます」等の誤爆防止）
2. マッチ幅を動的に算出：`min(20, original.length × 2)` 文字
3. `corrections[i].original` の完全一致位置を入力テキスト中から全件検索
4. 候補が複数ある場合は diff ブロックに最も近い位置のものを採用（最長一致優先）
5. 該当位置が diff ブロックの範囲（± マッチ幅）に収まればマッチとする
6. マッチしない場合は `diff_matched: false`（③タブには「参考（AI推定）」ラベルで表示）

**AI が文全体を書き換えた場合の扱い**

- diff は広範囲になるが、UI 上は正常に表示される（色付きブロックが広くなるだけ）
- corrections との対応は取れないが、③タブにはそのまま表示する
- ユーザーへの影響：「なぜ変わったか」がわかりにくくなるが、表示が崩れることはない

### 4.6 レスポンス JSON 構造（フロントエンドへの返却）

| フィールド | 型 | 説明 |
|------------|-----|------|
| `request_id` | string | リクエストの識別子（フロント生成。未送信時はサーバーで生成し両方をログに記録） |
| `status` | string | `"success"` \| `"partial"` \| `"error"` |
| `status_reason` | string \| null | partial・error の詳細理由。`"diff_timeout"` \| `"parse_fallback"` \| null |
| `warnings` | array | 注意事項のリスト。例：`["large_rewrite"]`（変更率 30% 超）。正常時は空配列。 |
| `corrected_text` | string | 校正済み全文 |
| `summary` | string \| null | 校正のサマリー（大幅書き換え時は警告文を含む） |
| `corrections` | array | AI が返した修正箇所の配列（参考情報） |
| `corrections[].original` | string | 修正前テキスト |
| `corrections[].corrected` | string | 修正後テキスト |
| `corrections[].reason` | string | 修正理由 |
| `corrections[].category` | string | 校正カテゴリ |
| `corrections[].diff_matched` | boolean | diff ブロックへの近傍マッチ成否。`false` の場合は「参考（AI推定）」として UI に表示。 |
| `diffs` | array | diff-match-patch＋後処理済みの差分ブロック配列 |
| `diffs[].type` | string | `"equal"` \| `"insert"` \| `"delete"` |
| `diffs[].text` | string | 差分テキスト |
| `diffs[].start` | number | **元テキスト（入力テキスト）基準の開始位置**。`insert` の場合は「元テキストのこの位置の直後に挿入」を意味する。 |
| `diffs[].position` | string \| null | `"after"`（insert 時のみ付与。delete・equal は null）。フロント再構築時の挿入点を明示。 |
| `diffs[].reason` | string \| null | 近傍マッチした corrections の reason（なければ null） |

---

## 5. API 設計

### 5.1 エンドポイント一覧

| メソッド | パス | 説明 |
|----------|------|------|
| POST | `/api/proofread` | AI 文書校正の実行 |
| GET | `/api/models` | 利用可能モデル一覧の取得 |
| GET | `/api/history` | 校正履歴一覧の取得（検索・フィルタ対応） |
| POST | `/api/history` | 校正結果の保存 |
| GET | `/api/history/{id}` | 特定履歴の取得 |
| PATCH | `/api/history/{id}` | メモの更新 |
| DELETE | `/api/history/{id}` | 特定履歴の削除 |
| DELETE | `/api/history` | 全履歴の削除 |
| POST | `/api/export/docx` | 校正済みテキストの .docx 生成 |
| GET | `/api/settings` | サーバー側設定の取得 |
| PUT | `/api/settings` | サーバー側設定の更新 |

> `/api/settings` はサーバー側管理の設定（履歴上限件数など）のみを扱う。モデル選択・校正オプションなどのクライアント設定は localStorage で管理し、このエンドポイントは使用しない。

### 5.2 POST /api/proofread

**Request**

```json
{
  "request_id": "uuid-v4-string",
  "text": "前処理済み入力テキスト（最大 8,000 文字）",
  "document_type": "email | report | official | other",
  "options": {
    "typo": true,
    "keigo": true,
    "terminology": true,
    "style": true,
    "legal": false,
    "readability": true
  },
  "model": "kimi-k2.5"
}
```

**Response（成功）**

```json
{
  "request_id": "uuid-v4-string",
  "status": "success",
  "status_reason": null,
  "warnings": [],
  "corrected_text": "校正済み全文",
  "summary": "3 件の修正を行いました。",
  "corrections": [
    {
      "original": "修正前",
      "corrected": "修正後",
      "reason": "理由",
      "category": "誤字脱字",
      "diff_matched": true
    }
  ],
  "diffs": [
    { "type": "equal",  "text": "問題ない部分", "start": 0,  "position": null,    "reason": null },
    { "type": "delete", "text": "修正前",       "start": 8,  "position": null,    "reason": "理由" },
    { "type": "insert", "text": "修正後",       "start": 8,  "position": "after", "reason": "理由" },
    { "type": "equal",  "text": "残り",         "start": 11, "position": null,    "reason": null }
  ]
}
```

**Response（大幅書き換え警告付き）**

```json
{
  "request_id": "uuid-v4-string",
  "status": "success",
  "status_reason": null,
  "warnings": ["large_rewrite"],
  "corrected_text": "校正済み全文",
  "summary": "AI が広範囲を書き換えました。内容を十分ご確認ください。",
  "corrections": [...],
  "diffs": [...]
}
```

**Response（partial）**

```json
{
  "request_id": "uuid-v4-string",
  "status": "partial",
  "status_reason": "diff_timeout",
  "warnings": [],
  "corrected_text": "校正済み全文（diff なし）",
  "summary": null,
  "corrections": [],
  "diffs": []
}
```

**Response（error）**

```json
{
  "request_id": "uuid-v4-string",
  "status": "error",
  "status_reason": "parse_fallback",
  "warnings": [],
  "corrected_text": "",
  "summary": null,
  "corrections": [],
  "diffs": []
}
```

### 5.3 POST /api/export/docx

**責務の明確化**：フロントエンドから `corrected_text` を直接送信する（パターン1）。履歴 ID 指定方式（パターン2）は将来の拡張とし MVP では実装しない。

**Request**

```json
{
  "corrected_text": "校正済みテキスト全文",
  "document_type": "email | report | official | other"
}
```

**Response**：`.docx` バイナリ（`Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document`）

### 5.4 GET /api/history（検索・フィルタ）

**Query Parameters**

| パラメータ | 型 | 説明 |
|-----------|-----|------|
| `q` | string | キーワード検索（入力テキスト・メモを対象に部分一致） |
| `document_type` | string | 文書種別フィルタ |
| `date_from` | string | 開始日（ISO 8601） |
| `date_to` | string | 終了日（ISO 8601） |
| `limit` | number | 取得件数（デフォルト 20） |
| `offset` | number | オフセット（ページネーション） |

> キーワード検索は **SQLite FTS5（ngram トークナイザ）** を使用する。unicode61 は日本語の分かち書きに対応せず「申請書」などがヒットしないケースがあるため、**ngram（n=2〜3）を使用し部分一致精度を確保する**。
> **⚠️ ビルド要件**：SQLite の ngram トークナイザは標準ビルドでは有効になっていない環境がある。`python -c "import sqlite3; conn=sqlite3.connect(':memory:'); conn.execute(\"CREATE VIRTUAL TABLE t USING fts5(x, tokenize='ngram')\")"` で事前に動作確認すること。使用できない環境では LIKE 検索にフォールバックする。
> FTS5 でヒットしない場合のフォールバックとして LIKE 検索を併用する（パフォーマンス低下が顕著になった場合は LIKE fallback を廃止し FTS5 のみとする）。

### 5.5 エラーレスポンス仕様

| HTTP ステータス | エラーコード | 状況 |
|-----------------|-------------|------|
| 400 | `text_too_long` | 入力文字数が 8,000 文字を超過 |
| 400 | `validation_error` | リクエストスキーマ不正 |
| 401 | `unauthorized` | 認証トークン不一致（MVP では認証無効。再有効化時に使用） |
| 504 | `ai_timeout` | AI API が 60 秒以内に応答しなかった |
| 502 | `ai_rate_limit` | AI API のレート制限に達した |
| 502 | `ai_invalid_response` | AI API がエラーレスポンスを返した |
| 502 | `ai_parse_error` | JSON パースが全リトライ失敗、かつ fallback 抽出も失敗（`status: "error"` で返却） |
| 500 | `internal_error` | サーバー内部エラー |

**エラーレスポンス形式**

```json
{
  "request_id": "uuid-v4-string",
  "error": "エラーコード",
  "message": "ユーザー向けメッセージ（日本語）"
}
```

---

## 6. ファイル入出力仕様

### 6.1 ファイル入力

| 形式 | ライブラリ | 処理概要 |
|------|-----------|----------|
| `.pdf` | pdf.js（Mozilla） | クライアントサイドでテキスト抽出 → 前処理（ページ区切り除去含む）→ **抽出結果プレビューをユーザーに表示し、確認・編集後に送信する**（自動送信しない）。**抽出品質は保証しない**（行順序崩壊・カラム混在・改行崩れが起きる場合がある）。ユーザー編集前提の設計とする。**画像のみの PDF はテキスト抽出不可（OCR 非対応）**。「テキストを抽出できませんでした。テキスト形式の PDF か、テキストを直接入力してください。」と通知。OCR 対応は将来拡張の余地あり。 |
| `.docx` | mammoth.js | クライアントサイドでテキスト抽出 → 前処理（3.3.2）→ **抽出結果プレビューをユーザーに表示し、確認後に送信する**（自動送信しない）。 |
| テキスト直接入力 | （なし） | テキストエリアに貼り付け・直接入力 → 前処理 → バックエンドへ送信 |

### 6.2 ファイル出力

| 形式 | 処理概要 |
|------|----------|
| `.docx` | バックエンド（python-docx）で校正済みテキストから生成。元の書式は再現しない（プレーンテキストベース）。ただし最小限の構造は保持する：**空行を段落区切りとして扱う**・**行頭が「・」「-」「数字+.」で始まる行はリストスタイルを適用する**。フロントエンドでバイナリレスポンスをダウンロード。 |
| テキストコピー | フロントエンドで Clipboard API を使用してクリップボードにコピー。 |

> **docx 出力の制約**：python-docx では元ファイルのレイアウト・書式を再現することはできません。校正済みテキストを標準スタイルで出力することのみを目的とし、書式の復元は対象外です。

---

## 7. 校正履歴管理

### 7.1 保存仕様

- 保存先：SQLite（バックエンド管理）。SQLAlchemy 経由で操作。Alembic でマイグレーション管理。
- 1 件あたりの保存データ：入力テキスト・校正結果 JSON・使用モデル・文書種別・校正日時・任意メモ・`truncated` フラグ
- **入力テキストの保存サイズ上限：8,000 文字**
- **校正結果 JSON の保存サイズ上限：100KB**（超過時は `corrections` を切り捨てて `summary` のみ保存し、`truncated: true` を記録）
- デフォルト保存件数上限：50 件（設定で 1〜200 件に変更可能）
- 超過時は最古のものから自動削除
- **総容量上限：20MB**（SQLite ファイルサイズが 20MB を超えた場合、古いレコードから自動削除して上限内に収める）

**`truncated: true` の場合の UI 表現**

- 履歴一覧：「⚠ 詳細省略」バッジを表示
- 履歴詳細：「データサイズ超過のため校正詳細は保存されていません。校正済みテキストのみ表示します。」と表示し、③タブを非表示にする

### 7.2 履歴一覧表示・検索

- 校正日時（降順）・文書種別・先頭 50 文字のプレビューを一覧表示
- **キーワード検索**：入力テキスト・メモを対象に部分一致（SQLite LIKE）
- **日付フィルタ**：開始日〜終了日で絞り込み
- **文書種別フィルタ**：ドロップダウンで絞り込み
- 履歴クリックで校正結果を復元・再表示
- メモ・コメントを追記できるテキストフィールドを設ける
- 履歴個別削除・全件削除ボタンを設ける

---

## 8. セキュリティ設計

### 8.1 API キー管理

- API キーはバックエンドの `.env` で管理し、環境変数として参照する
- フロントエンドへの露出は禁止。API レスポンスにも含めない
- `.env` は `.gitignore` に登録し、バージョン管理対象外とする
- `.env.example` をリポジトリに含め、必要なキー名のみ記載する

### 8.2 認証

**MVP では認証なし（localhost 専用）**

MVP（ローカル環境での個人利用）では認証を無効化している。コードはコメントアウトで残されており、将来 Web 公開時に再有効化可能。

> **⚠️ 認証は無効化されています。本アプリは localhost 限定での使用を前提としています。**

| 項目 | 仕様 |
|------|------|
| 認証状態 | MVP では無効（コードはコメントアウトで保留） |
| 再有効化 | `docs/superpowers/specs/2026-03-22-auth-removal-design.md` の再有効化手順を参照 |
| **Origin チェック** | サーバー側でも `Origin` ヘッダーを検証し、許可リスト外のオリジンからのリクエストを拒否する。**これはセキュリティ対策ではなく誤操作防止**（curl 等の直接リクエストは防げない）として位置付ける。 |
| **XSS 対策** | React コンポーネント内で dangerouslySetInnerHTML の使用を禁止する。diff 表示・テキストレンダリングはすべて React の通常のデータバインディング（JSX）で行い、HTML を直接挿入しない。 |
| **起動時警告** | フロントエンド初回起動時に「本アプリは localhost 限定での使用を前提としています。外部ネットワークへの公開は絶対に行わないでください。」をモーダルで表示し、確認ボタンで閉じる。 |

### 8.3 CORS 設定

許可オリジンは `.env` の `CORS_ORIGINS` で管理し、Vite ポート変更に対応できるようにする。

```python
# .env.example
CORS_ORIGINS=http://localhost:5173

# main.py
import os
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "PUT"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
```

### 8.4 セキュリティ警告 UI

入力エリアの上部に常時以下の警告を表示する。

> ⚠️ 本ツールはテキストを外部 AI サービスに送信します。個人情報・機密情報を含む文書の入力はお控えください。

---

## 9. ログ設計

### 9.1 ログレベル・出力先・ローテーション

| レベル | 出力先 | ローテーション | 保持期間 |
|--------|--------|--------------|---------|
| ERROR | `logs/error.log` + コンソール | 10MB でローテーション・最大 5 世代保持 | 30 日 |
| WARNING | `logs/app.log` + コンソール | 10MB でローテーション・最大 3 世代保持 | 7 日 |
| INFO | コンソールのみ | - | - |

> RotatingFileHandler（Python 標準）を使用する。

### 9.2 記録するイベント

| イベント | レベル | 記録内容 |
|----------|--------|---------|
| AI API 呼び出し失敗 | ERROR | `request_id`・エンドポイント・ステータスコード・エラーメッセージ・モデル名 |
| AI レスポンス JSON パース失敗 | WARNING | `request_id`・モデル名・リトライ回数・raw レスポンスの **SHA-256 ハッシュ**（本文は記録しない）・文字数 |
| fallback 発動 | WARNING | `request_id`・fallback 理由 |
| diff 計算タイムアウト | WARNING | `request_id`・入力文字数 |
| **大幅書き換え検知** | WARNING | `request_id`・入力文字数・変更文字数・変更率 |
| **diff 短小ブロック圧縮** | INFO | `request_id`・圧縮前ブロック数・圧縮後ブロック数（本文なし。デバッグ用。） |
| リクエストバリデーション失敗 | WARNING | `request_id`・エンドポイント・エラー内容 |
| サーバー内部エラー | ERROR | `request_id`・スタックトレース |
| DB 操作エラー | ERROR | `request_id`・操作内容・エラー内容 |

> **個人情報保護**：ログに入力テキストの本文は記録しない。`request_id` で API リクエストとログを紐付ける。

---

## 10. 非機能要件

| 項目 | 要件 |
|------|------|
| パフォーマンス（UI 処理） | ファイル読み込み〜バックエンドへの送信開始まで 3 秒以内 |
| パフォーマンス（AI 応答） | 外部サービス依存のため保証なし。タイムアウトは 60 秒。処理中はスピナーを表示。 |
| パフォーマンス（diff 計算） | 文字単位 diff は 5 秒でタイムアウト。超過時は行単位 diff にフォールバック（大幅高速化）。行単位 diff も 1 秒以内に完了しない場合のみ diff なし（`status_reason: "diff_timeout"`）で返却。 |
| 入力上限 | 8,000 文字（超過時は送信不可） |
| ネットワーク | ローカル環境（localhost）限定。外部公開不可。 |
| セキュリティ | API キーはバックエンド管理。CORS localhost 限定。MVP では認証無効（再有効化可能）。 |
| プライバシー | 入力テキストはログに記録しない。外部 AI サービスへの送信についてはユーザーへ警告 UI で明示。 |
| アクセシビリティ | キーボード操作対応。フォントサイズはブラウザ設定に追従。 |
| 保守性 | ツールを独立したモジュールファイルとして分離し、サイドメニューへの登録のみで機能追加できる構造とする。 |
| エラーハンドリング | 全エラーコードに対応した日本語メッセージを表示。「再試行」ボタンを提供。 |
| スケーラビリティ | SQLite を SQLAlchemy 経由で使用し、将来的な PostgreSQL 移行を容易にする。スキーマ変更は Alembic で管理。全文検索は最初から FTS5 前提のテーブル設計とする。設定は将来的にすべてサーバー管理に移行できる構造にしておく（localStorage はキャッシュ扱い）。 |

---

## 11. ディレクトリ構成（MVP）

```
govassist/
├── frontend/                        # React（Vite）
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   ├── public/
│   └── src/
│       ├── main.jsx                 # エントリーポイント
│       ├── App.jsx                  # 全体レイアウト・ルーティング
│       ├── css/
│       │   ├── base.css             # リセット・基本スタイル
│       │   ├── layout.css           # ヘッダー・サイドメニュー・メインエリア
│       │   └── components.css       # ボタン・テキストエリアなど共通 UI
│       ├── components/
│       │   ├── SideMenu.jsx         # サイドメニュー
│       │   ├── Header.jsx           # ヘッダー・モデル切替セレクタ
│       │   └── common/              # 共通 UI コンポーネント
│       └── tools/
│           ├── proofreading/
│           │   ├── Proofreading.jsx # AI 文書校正メイン
│           │   ├── InputArea.jsx    # テキスト入力・ファイルアップロード
│           │   ├── OptionPanel.jsx  # 校正オプション選択
│           │   ├── ResultView.jsx   # 校正結果（3タブ）表示
│           │   ├── DiffView.jsx     # diff ベースのハイライト・比較表示
│           │   └── preprocess.js    # テキスト前処理ユーティリティ
│           ├── history/
│           │   └── History.jsx      # 校正履歴一覧・検索・再閲覧
│           └── settings/
│               └── Settings.jsx     # 設定画面
│
└── backend/                         # Python（FastAPI）
    ├── main.py                      # FastAPI アプリ起動・ルーター登録・CORS 設定
    ├── .env                         # API キー・認証トークン等（Git 管理外）
    ├── .env.example                 # .env のサンプル（Git 管理対象）
    ├── requirements.txt
    ├── database.py                  # SQLAlchemy 設定・SQLite 接続
    ├── models.py                    # DB モデル定義（truncated フラグ含む）
    ├── schemas.py                   # Pydantic スキーマ定義
    ├── logs/                        # ログ出力ディレクトリ（Git 管理外）
    ├── migrations/                  # Alembic マイグレーションファイル
    ├── routers/
    │   ├── proofread.py             # POST /api/proofread
    │   ├── history.py               # GET/POST/PATCH/DELETE /api/history
    │   ├── export.py                # POST /api/export/docx
    │   ├── models_router.py         # GET /api/models
    │   └── settings.py              # GET/PUT /api/settings（サーバー設定のみ）
    └── services/
        ├── ai_client.py             # さくらの AI Engine API クライアント
        ├── prompt_builder.py        # プロンプト生成ロジック
        ├── response_parser.py       # AI レスポンスの JSON パース・バリデーション・リトライ・fallback
        ├── diff_service.py          # diff-match-patch による差分計算・corrections 近傍マッチ
        └── docx_exporter.py         # python-docx による .docx 生成
```

---

## 12. 改訂履歴

| バージョン | 日付 | 内容 |
|-----------|------|------|
| v1.0.0 | 2026/03/21 | 初版作成（ヒアリング結果に基づく MVP 設計） |
| v1.1.0 | 2026/03/21 | 技術スタックを React（Vite）＋ FastAPI に変更 |
| v1.2.0 | 2026/03/21 | レビュー指摘を全件反映（position 廃止・diff 生成、JSON パース耐性、入力制限、モデル設定テーブル、APIスキーマ、ログ設計等） |
| v1.3.0 | 2026/03/21 | 第2回レビュー指摘を全件反映。diff と corrections の紐付け戦略明確化（案A採用）、AI 出力の粒度制約・大幅書き換え禁止をプロンプトに追加、fallback 抽出ロジック定義、入力上限を 8,000 文字に修正・根拠明記、エラーコード細分化、/api/settings の責務分離、トークン認証の限界明記・ローカル限定を設計方針に追記、CORS 具体化、diff 表示仕様（色・粒度）明記、truncated フラグ追加、SQLite FTS5 言及、ログローテーション定義、request_id によるトレース設計追加 |
| v1.4.0 | 2026/03/21 | 第3回レビュー指摘を全件反映。`diffs[].start` を元テキスト基準に統一・`insert` に `position: "after"` 付与、diff 後処理（連続同種ブロックマージ）追加、status を success/partial/error の3段階に分離・各 UI 挙動定義、近傍マッチ幅を動的算出（min(20, original.length×2)）に変更、`diff_matched: false` に「参考（AI推定）」ラベル追加、`/api/export/docx` のリクエスト形式明確化、`request_id` をサーバー側でも生成・両方ログに記録、CORS オリジンを `.env` 環境変数化、履歴の総容量上限（20MB）追加、PDF 仕様に「OCR 非対応・将来拡張余地あり」明記、モデル設定テーブルに temperature 拡張性メモ追記、セクション番号重複修正 |
| v1.5.0 | 2026/03/21 | 第4回レビュー指摘を全件反映。フロントの corrected_text 再構築禁止を設計方針・処理フロー・diff 仕様に明記、diffs の適用順序保証（delete→insert ペア・同一 start 固定）をバックエンド責務に追加、diff 後処理②（短小ブロック吸収・3文字未満統合）追加、近傍マッチにガード条件（4文字未満マッチ禁止）と最長一致優先を追加、fallback に再プロンプト段階を追加（regex 前に LLM 再フォーマット）、partial 時の corrected_text を常時目立つ位置に表示、localStorage をキャッシュ扱いに変更・設定テーブルにサーバー移行予定を明記、SQLite 検索を最初から FTS5 前提に変更、docx 出力に空行→段落・箇条書き検出を追加、ログの raw レスポンスを SHA-256 ハッシュに変更、トークン保存の注意事項に「同一 PC 内の他プロセスからも保護されない」を追記、UI に「表示は差分ベース／コメントは AI 推定」の常時表示を追加 |
| v1.6.0 | 2026/03/21 | 第5回レビュー指摘を全件反映。フロントの reduce 的逐次レンダリング方針を設計方針・処理フロー・diff 仕様に追加、PDF/docx ファイル抽出後の必須プレビュー＋手動編集欄を追加、diff 短小ブロック圧縮の副作用（細かい修正が消える可能性）と圧縮前ログ保存を明記、近傍マッチ 4 文字未満の扱いを補足（③タブのみ表示）、大幅書き換え検知（変更率 30% 超）と warnings フィールドを追加、status_reason フィールドを追加（diff_timeout / parse_fallback）・UI 分岐テーブルを詳細化、FTS5 トークナイザを unicode61 から ngram に変更し LIKE fallback を併用、起動時 localhost 限定警告モーダルを追加、Origin チェックをサーバー側に追加、ログに大幅書き換え検知・diff 圧縮（INFO）イベントを追加 |
| v1.7.0 | 2026/03/21 | 第6回レビュー指摘を全件反映。diff 短小ブロック吸収の閾値を 3 文字未満 → 2 文字未満に緩和（助詞＋動詞修正が消えるリスク軽減）、diffs の順序正規化をバックエンド責務として明文化（equal を挟んだ delete/insert の並べ替えを明示）、`start` をデバッグ用途に限定しフロントレンダリングは順序のみ依存に変更、corrections の全エントリが壊れている場合の全削除 OK ポリシーを明文化、large_rewrite の変更率計算を delete+insert のみに変更（equal 除外・改行整理等の誤検知防止）、localStorage にスキーマバージョン（`version: 1`）を追加しマイグレーション設計を整備 |
| v1.8.0 | 2026/03/21 | 第7回レビュー指摘を全件反映。diff 正規化アルゴリズムを4ルールで明文化（equal 跨ぎ禁止を最重要ルールとして明示）、corrections マッチの競合解決ルールを追加（1 diff に reason 最大1件・消費型）、JSON 再プロンプトの内容を固定（前回レスポンスを貼付して再フォーマット依頼）、diff タイムアウト時に行単位 diff へのフォールバックを追加（全失敗時のみ③タブ表示）、large_rewrite 判定を「最大連続変更ブロック長 ÷ 全体長」との AND 条件に変更（誤検知防止）、`enable_diff_compaction` フラグを MVP から実装、PDF 抽出品質を「保証しない・ユーザー編集前提」と明記、localStorage マイグレーションをリセット優先から移行優先に変更、Origin チェックを「誤操作防止」と明確化、`dangerouslySetInnerHTML` 禁止を XSS 対策として追記、FTS5 ngram のビルド要件確認コマンドと環境依存注意を追加 |

---

## 13. 実装タスクリスト（MVP）

MVP 実装を Claude Code のセッション単位で進めるためのタスクリスト。各タスクは 1 セッション（2〜4 ファイル程度の作成・変更）に収まる粒度としている。

### Phase 1: バックエンド基盤（Task 1–3）

| タスク | 名称 | 対応設計書セクション | 前提タスク | 作成・変更ファイル | 内容 |
|--------|------|-------------------|-----------|-------------------|------|
| 1 | バックエンドプロジェクトのセットアップ | §2.2, §9, §11 | なし | `backend/requirements.txt`, `backend/main.py`, `backend/schemas.py`, `backend/.env.example`, `backend/logs/` | FastAPI app 雛形・Pydantic スキーマ定義（ProofreadRequest/Response 等）・`.env` テンプレート・logging 設定（RotatingFileHandler） |
| 2 | データベースセットアップ | §7, §11 | 1 | `backend/database.py`, `backend/models.py`, `backend/migrations/` | SQLAlchemy エンジン・セッション設定、History テーブルモデル（truncated フラグ含む）、Alembic 初期化＋初回マイグレーション、SQLite FTS5 ngram トークナイザ動作確認 |
| 3 | 認証ミドルウェア & CORS | §8.2, §8.3 | 1 | `backend/main.py` | Bearer token 認証デペンデンシー追加、CORS ミドルウェア追加（`CORS_ORIGINS` 環境変数対応）、Origin チェックロジック |

### Phase 2: バックエンド AI サービス（Task 4–7）

| タスク | 名称 | 対応設計書セクション | 前提タスク | 作成・変更ファイル | 内容 |
|--------|------|-------------------|-----------|-------------------|------|
| 4 | AI クライアントサービス | §4.1 | 1 | `backend/services/ai_client.py` | さくらの AI Engine API 呼び出し（OpenAI 互換 REST API）、タイムアウト 60 秒、エラーハンドリング（rate limit / timeout / API error） |
| 5 | プロンプトビルダー | §4.3 | 1 | `backend/services/prompt_builder.py` | システムプロンプト（固定）＋ユーザープロンプト（動的生成）、文書種別・校正オプションに応じたプロンプト構築 |
| 6 | レスポンスパーサー | §4.4 ステップ1–4, §9.2 | 4 | `backend/services/response_parser.py` | JSON パース（コードブロック除去 → パース → Pydantic バリデーション）、リトライロジック（最大3回）＋再プロンプト（固定文言）、fallback 抽出（regex → 平文 → error） |
| 7 | Diff サービス | §4.4 ステップ5–11, §4.5 | 1 | `backend/services/diff_service.py` | diff-match-patch で差分計算（タイムアウト 5 秒 → 行単位 diff フォールバック）、後処理①連続同種ブロックマージ、後処理②短小ブロック吸収（`enable_diff_compaction` フラグ対応）、順序正規化（4ルール）、corrections 近傍マッチ（動的幅・4文字未満ガード・消費型）、大幅書き換え検知 |

### Phase 3: バックエンド API ルート（Task 8–11）

| タスク | 名称 | 対応設計書セクション | 前提タスク | 作成・変更ファイル | 内容 |
|--------|------|-------------------|-----------|-------------------|------|
| 8 | Models & Settings ルート | §4.2, §5.1 | 2, 3 | `backend/routers/models_router.py`, `backend/routers/settings.py`, `backend/main.py` | GET /api/models（モデル設定テーブル参照）、GET/PUT /api/settings（サーバー設定 CRUD） |
| 9 | Proofread ルート | §4.4, §5.2, §5.5 | 4, 5, 6, 7, 8 | `backend/routers/proofread.py`, `backend/main.py` | POST /api/proofread：AI client → prompt builder → response parser → diff service の統合、入力文字数チェック、X-Request-ID 処理、エラーレスポンス生成 |
| 10 | History ルート | §5.4, §7, §8.2 | 2, 3 | `backend/routers/history.py`, `backend/main.py` | CRUD + 検索（FTS5 ngram 全文検索＋LIKE フォールバック）、保存件数上限・総容量上限（20MB）の自動削除、truncated フラグ対応 |
| 11 | DOCX Export ルート | §5.3, §6.2 | 3 | `backend/routers/export.py`, `backend/services/docx_exporter.py`, `backend/main.py` | POST /api/export/docx：python-docx でプレーンテキストベースの .docx 生成（段落区切り・箇条書き検出） |

### Phase 4: フロントエンド基盤（Task 12–14）

| タスク | 名称 | 対応設計書セクション | 前提タスク | 作成・変更ファイル | 内容 |
|--------|------|-------------------|-----------|-------------------|------|
| 12 | フロントエンドプロジェクトセットアップ & CSS | §2.2, §3.1 | なし | `frontend/`（Vite + React 18 プロジェクト）, `css/base.css`, `css/layout.css`, `css/components.css` | Vite プロジェクト作成、素の CSS によるリセット・基本スタイル・レイアウト定義 |
| 13 | App Shell（レイアウト・ルーティング） | §2.3, §3.1, §3.2 | 12 | `App.jsx`, `components/SideMenu.jsx`, `components/Header.jsx` | 全体レイアウト（サイドメニュー＋メインエリア）、ツール一覧・ページ切替、モデル切替セレクタ、React Router ルーティング |
| 14 | API クライアント & 認証フロー | §5, §8.2, §8.4 | 12 | API 通信ユーティリティモジュール, 認証関連コンポーネント | fetch ラッパー（X-Request-ID 付与・Authorization header）、localStorage によるトークン保存・読み込み、起動時 localhost 限定警告モーダル、ログイン画面（トークン入力）— 認証エラー時のリダイレクト |

### Phase 5: フロントエンド AI 文書校正ツール（Task 15–19）

| タスク | 名称 | 対応設計書セクション | 前提タスク | 作成・変更ファイル | 内容 |
|--------|------|-------------------|-----------|-------------------|------|
| 15 | 入力エリア | §3.3.1, §3.3.2, §6.1, §8.4 | 14 | `tools/proofreading/InputArea.jsx`, mammoth.js / pdf.js 依存追加 | テキストエリア（最低10行表示）、ファイルアップロード（.docx/.pdf）＋ドラッグ＆ドロップ、mammoth.js / pdf.js によるテキスト抽出、抽出結果プレビュー（ユーザー確認後に送信）、文書種別セレクタ、文字数カウンター（8,000文字上限・超過時ボタン無効化）、セキュリティ警告表示 |
| 16 | テキスト前処理 & 校正オプション | §3.3.2, §3.3.3 | 14 | `tools/proofreading/preprocess.js`, `tools/proofreading/OptionPanel.jsx` | 前処理ルール実装（改行正規化・空白トリム・ページ区切り除去・NULL文字除去）、校正オプションチェックボックス（6項目） |
| 17 | 結果表示 — フレームワーク & タブ③ コメント一覧 | §3.3.4, §4.6 | 14 | `tools/proofreading/ResultView.jsx` | 3タブ構成のフレームワーク、タブ③ コメント一覧表示、`diff_matched: false` の「参考（AI推定）」ラベル表示、status による UI 分岐（success/partial/error）、large_rewrite 警告表示 |
| 18 | 結果表示 — タブ① ハイライト & タブ② 比較 | §3.3.4, §4.5 | 17 | `tools/proofreading/DiffView.jsx` | タブ① ハイライト表示（reduce 的逐次レンダリング・順序のみ依存）、タブ② 比較表示（左右並列・スクロール同期）、ツールチップ（reason ポップアップ）、「表示は差分ベース／コメントはAI推定」の常時表示 |
| 19 | アクションボタン & ステータス管理 | §3.3.5, §3.3.6 | 15, 16, 17, 18 | `tools/proofreading/Proofreading.jsx`, 各子コンポーネント | 校正実行ボタン（処理中無効化＋スピナー）、クリアボタン、校正済みテキストのコピー（Clipboard API）、Word ダウンロード（POST /api/export/docx → バイナリDL）、履歴に保存ボタン、処理中状態の UI（スピナー・タイムアウト・再試行ボタン）、エラーメッセージ表示 |

### Phase 6: フロントエンド他ツール（Task 20–21）

| タスク | 名称 | 対応設計書セクション | 前提タスク | 作成・変更ファイル | 内容 |
|--------|------|-------------------|-----------|-------------------|------|
| 20 | 履歴パネル | §7, §5.4 | 14 | `tools/history/History.jsx` | 履歴一覧表示（日時降順・文書種別・先頭50文字プレビュー）、キーワード検索・日付フィルタ・文書種別フィルタ、履歴クリックで結果復元・再表示、メモ追記・個別削除・全件削除、truncated レコードの警告表示 |
| 21 | 設定パネル | §3.4 | 14 | `tools/settings/Settings.jsx` | モデル選択（GET /api/models から動的生成）、デフォルト文書種別・校正オプションの初期値設定、localStorage への保存（`version: 1` スキーマ）、localStorage マイグレーション対応、履歴保存件数上限の設定（PUT /api/settings） |

### Phase 7: 統合（Task 22）

| タスク | 名称 | 対応設計書セクション | 前提タスク | 作成・変更ファイル | 内容 |
|--------|------|-------------------|-----------|-------------------|------|
| 22 | エンドツーエンド統合テスト & 仕上げ | 全セクション | 9–21 | 既存ファイルの修正 | フロントエンド ↔ バックエンド通信の動作確認、エラーケースの動作確認（文字数超過・AI タイムアウト・JSON パース失敗等）、各 status（success/partial/error）の UI 表示確認、diff 表示の精度確認（日本語テキストでの動作確認）、ログ出力の確認 |

### 依存関係図

```
Phase 1:  [Task 1] ─→ [Task 2] ─→ [Task 3]
Phase 2:  [Task 1] ─→ [Task 4] ─→ [Task 6]
           [Task 1] ─→ [Task 5]
           [Task 1] ─→ [Task 7]
Phase 3:  [Task 2]+[Task 3] ─→ [Task 8] ─→ [Task 9]
           [Task 2]+[Task 3] ─→ [Task 10]
           [Task 3] ─→ [Task 11]
Phase 4:  [Task 12] ─→ [Task 13] ─→ [Task 14]
Phase 5:  [Task 14] ─→ [Task 15]
           [Task 14] ─→ [Task 16]
           [Task 14] ─→ [Task 17] ─→ [Task 18]
           [Task 15]+[Task 16]+[Task 17]+[Task 18] ─→ [Task 19]
Phase 6:  [Task 14] ─→ [Task 20]
           [Task 14] ─→ [Task 21]
Phase 7:  [Task 9]〜[Task 21] 全完了 ─→ [Task 22]
```

> **並列実行の可能性**：Phase 4（Task 12–14）は Phase 1–3 と独立して並列に進められる。Phase 5 内では Task 15・16・17 を並列に開始できる。Phase 6 の Task 20・21 も Task 14 完了後なら並列に進められる。
