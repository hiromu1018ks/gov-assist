# Playwright Dogfooding Design

## Overview

Playwright MCPを使用してGovAssistの全機能をインタラクティブにドッグフーディングし、機能や仕様の不備を発見する。

## Scope

- 対象: 実装済みの全機能（校正、履歴CRUD、DOCXエクスポート、設定、モデル選択）
- AI API: 本物のSAKURA AI Engine APIを使用（APIキー必須）
- テストデータ: 複数パターン（短文、長文、記号混じり、エッジケース）
- 方式: シナリオ順次実行（体系的な網羅）

## Prerequisites

- Frontend dev server: `npm run dev` (port 5173)
- Backend server: `uvicorn main:app --reload` (port 8000)
- `.env` に `AI_ENGINE_API_KEY` が設定済み

## Test Scenarios

### Scenario 1: Startup & Initial Display

- `http://localhost:5173` を開く
- BootSequenceアニメーションの動作確認
- WarningModalの表示→閉じる
- 初期画面のレイアウト確認（Header、SideMenu、メインエリア）
- MatrixRain背景の表示

### Scenario 2: Proofreading — Basic Flow

- テストデータ①（短いメール）を入力
- 文書種別「メール」を選択
- オプションをデフォルトで実行
- 結果の3タブ（原文/修正文/差分）を確認
- コピー、DOCXダウンロード、履歴保存の各アクション

### Scenario 3: Proofreading — Multiple Patterns

- テストデータ②（長めの文書）で校正
- テストデータ③（記号・英数字混じり）で校正
- オプション変更時の動作確認
- リトライ機能の確認

### Scenario 4: File Upload

- .docxファイルのアップロード（ドラッグ&ドロップ含む）
- .pdfファイルのアップロード
- 不正ファイルのリジェクト確認

### Scenario 5: History Management

- 履歴一覧の表示
- 検索機能（キーワード検索）
- フィルタ（文書種別、日付範囲）
- ページネーション
- 詳細表示→メモ編集→保存
- 個別削除、全削除

### Scenario 6: Settings

- AIモデルの切替
- デフォルト文書種別の変更
- デフォルトオプションの変更
- サーバー設定（履歴上限）の保存

### Scenario 7: Edge Cases

- 空入力で送信
- 8000文字ギリギリの入力
- 非常に短いテキスト（1文字）
- 特殊文字（絵文字、記号のみ）

### Scenario 8: UI/UX

- SideMenuのナビゲーション
- 無効化メニュー項目の表示
- リサイズ時の挙動
- 各種アニメーション

## Deliverables

- 発見した不具合・仕様不備のリスト
- スクリーンショット付きレポート
