# Hacker Theme Design Spec

**Date**: 2026-03-23
**Status**: Approved
**Scope**: Frontend visual overhaul — entire application

## Overview

GovAssistのフロントエンドを「ハッカー端末」風のビジュアルに全面改装する。Matrix/ターミナルの雰囲気をベースに、Cyberpunkの構造的要素（ボックス描画文字、ステータス表示、プログレスバー）を融合。tmux風のパネル分割レイアウトを採用し、既存の管理画面スタイルを根本から変更する。遊び心のある演出（ブートシーケンス、グリッチ、ランダムメッセージ）で没入感を高める。

## Design Decisions

| 項目 | 決定 |
|------|------|
| ベーススタイル | Matrix/ターミナル + Cyberpunk要素融合 |
| レイアウト | tmux風ターミナルマルチプレクサ |
| アニメーション | フルインパクト（音なし、パフォーマンス優先） |
| フォント | Share Tech Mono + 日本語フォールバック |
| スコープ | 画面全体一括変更 |
| Diff表示 | エフェクト付き（赤glow+グリッチ / 緑glow+ボーダー） |

## 1. Layout — tmux風パネル分割

### 構造

既存のHeader（48px）+ Sidebar（200px）+ Mainの管理画面レイアウトを廃止し、tmux風のパネル分割レイアウトに変更。

```
┌──────────────────────────────────────────────────┐
│ ▶ GOV_ASSIST v2.0  ● ONLINE │ AI: kimi-k2.5     │  ← 上部ステータスバー
├────────────┬─────────────────────────────────────┤
│            │                                     │
│  MODULES   │   [ proofread::input ]              │  ← 左パネル + メインパネル
│  ▸ proof   │   ┌─────────────────────────────┐   │     (1px緑の罫線で区切る)
│  ○ trans   │   │  textarea / result area     │   │
│  ○ summ    │   │                             │   │
│  ○ fmt     │   └─────────────────────────────┘   │
│  ────────  │   [EXECUTE] [CLEAR]     0/8000      │
│  ○ history │                                     │
│  ○ settings│                                     │
├────────────┴─────────────────────────────────────┤
│ ● READY                    history:12 | db:2.1MB │  ← 下部システムバー
└──────────────────────────────────────────────────┘
```

### 各パネル

- **上部ステータスバー**: アプリ名 + 接続状態 + AIモデル。`#0d1117`背景、下部にグラデーションライン
- **左パネル（モジュール）**: ナビゲーション。アクティブ項目に左ボーダー+glow背景。非アクティブは`○`で半透明。幅200px維持
- **メインパネル**: ツールのコンテンツ領域。パネルタイトルを `[ tool_name::section ]` 形式で表示
- **下部システムバー**: 接続状態、履歴数、DBサイズなどのシステム情報。ランダムステータスメッセージを表示

### 捨てるもの

- 独立したHeader（高さ48px）
- 独立したSidebar（幅200px）— レイアウトとしては残すが、視覚的にはtmuxパネルの一部
- カード型の白背景コンポーネント
- 大きいborder-radius（`--radius-lg: 8px`等）
- 管理画面的なレイアウト感

## 2. Color Palette — デザイントークン

### 基本パレット

```css
--color-bg:              #000000    /* メイン背景 */
--color-bg-secondary:    #0a0a0a    /* カード/パネル背景 */
--color-bg-elevated:     #0d1117    /* ステータスバー/ヘッダー */
--color-primary:         #00ff41    /* メイングリーン */
--color-primary-hover:   #33ff66    /* ホバー時 */
--color-primary-active:  #00cc33    /* アクティブ時 */
--color-accent:          #00ffff    /* シアンアクセント */
```

### テキスト

```css
--color-text:            #c0ffd8    /* 主要テキスト（暗めの緑で可読性確保） */
--color-text-bright:     #00ff41    /* 見出し・強調 */
--color-text-muted:      #4a6a52    /* 補助テキスト */
```

### ステータス

```css
--color-success:         #39ff14
--color-danger:          #ff0040
--color-warning:         #ffaa00
--color-info:            #00ffff    /* accentと同じ */
```

### ボーダー

```css
--color-border:          #00ff4133  /* デフォルト（低透明度の緑） */
--color-border-focus:    #00ff41    /* フォーカス時 */
```

### Diff表示

```css
--color-diff-delete-bg:  rgba(255, 0, 64, 0.25)   /* 削除: 暗赤背景 */
--color-diff-delete-text:#ff2244                    /* 削除テキスト */
--color-diff-insert-bg:  rgba(0, 255, 65, 0.25)    /* 追加: 暗緑背景 */
--color-diff-insert-text:#44ff88                    /* 追加テキスト */
```

### Glowトークン（新規）

```css
--glow-primary:  0 0 8px #00ff41
--glow-accent:   0 0 8px #00ffff
--glow-danger:   0 0 8px #ff0040
--glow-success:  0 0 8px #39ff14
```

### トークン対応表（旧 → 新）

| 旧トークン | 旧値 | 新値 | 新トークン |
|-----------|------|------|-----------|
| `--color-text` | `#333` | `#c0ffd8` | 同名 |
| `--color-text-secondary` | `#666` | `#00ff41` | `--color-text-bright` |
| `--color-text-muted` | `#999` | `#4a6a52` | 同名 |
| `--color-bg` | `#f5f5f5` | `#000000` | 同名 |
| `--color-bg-white` | `#fff` | `#0a0a0a` | `--color-bg-secondary` |
| `--color-bg-hover` | `#e8e8e8` | `#00ff4115` | 同名 |
| `--color-bg-active` | `#ddd` | `#00ff4125` | 同名 |
| `--color-border` | `#ddd` | `#00ff4133` | 同名 |
| `--color-border-focus` | `#4a90d9` | `#00ff41` | 同名 |
| `--color-primary` | `#4a90d9` | `#00ff41` | 同名 |
| `--color-primary-hover` | `#357abd` | `#33ff66` | 同名 |
| `--color-primary-active` | `#2a6aad` | `#00cc33` | 同名 |
| `--color-danger` | `#d94a4a` | `#ff0040` | 同名 |
| `--color-danger-hover` | `#bd3535` | `#ff3366` | 同名 |
| `--color-warning` | `#f0ad4e` | `#ffaa00` | 同名 |
| `--color-success` | `#5cb85c` | `#39ff14` | 同名 |

## 3. Typography

### フォント

```css
--font-mono: 'Share Tech Mono', 'Courier New', monospace;
--font-body: 'Share Tech Mono', 'Hiragino Sans', 'Noto Sans JP', 'Yu Gothic', monospace;
```

- **Share Tech Mono**をGoogle Fontsから読み込み、全体のベースフォントとする
- 日本語文字はシステムフォントにフォールバック
- `pre`やコードブロックは`--font-mono`（Share Tech Monoのみ）
- 日本語の可読性を考慮し、長文テキスト（校正結果など）では`--font-body`を使用

### サイズ

既存のフォントサイズスケールを維持するが、base sizeを13-14pxに調整（端末風に少し小さく）。

### テキスト効果

- 見出し: `text-shadow: 0 0 8px #00ff41` （グリーングロー）
- 重要テキスト: `text-shadow: 0 0 6px #00ff41` （やや弱め）
- 通常テキスト: glowなし（可読性優先）
- リンク/アクション: ホバー時にglowが強くなる

## 4. Components

### Buttons

```
Primary:  背景 #00ff41 / 文字 #000 / box-shadow glow / 角2px / 太字
Secondary: 透明 / ボーダー #00ff4133 / 文字 #00ff41 / opacity 0.7
Danger:    透明 / ボーダー #ff004033 / 文字 #ff0040 / red glow
Danger-solid: 背景 #ff0040 / 文字 #fff / box-shadow red glow
```

- 角丸を2pxに制限（角張った印象）
- ホバー時にglowが強くなる
- `[ EXECUTE ]` のように角括弧付きラベルを使用

### Inputs

```
Default:  背景 #00ff4108 / ボーダー #00ff4122 / 文字 #00ff41 / 角2px
Focus:    ボーダー #00ff41 / box-shadow glow / カーソル緑点滅
Disabled: opacity 0.3
```

### Checkbox

```
Unchecked: ボーダー #00ff4133 / 1px角 / 14px
Checked:   ボーダー #00ff41 / 背景 #00ff4115 / ✓ グリーン + glow
```

### Tabs

下線スタイルを維持。アクティブタブは緑glow付き下線（`border-bottom: 2px solid #00ff41` + `text-shadow`）。

### Modal

```
Overlay:   背景 rgba(0,0,0,0.7)
Container: 背景 #0a0a0a / ボーダー #00ff4133 / 角3px / box-shadow glow
```

- `[ WARNING ]` のようなヘッダーラベルを角括弧付きで表示

### Drop Zone

```
Default:   ボーダー #00ff4133 / 背景 transparent / 角2px
Active:    ボーダー #00ff41 / 背景 #00ff4110 / glow
```

### Spinner

既存のCSSアニメーションを維持しつつ、色をグリーンに変更。グリーングロー付き。

## 5. Diff Display

### ハイライト表示

- **削除（元テキスト）**: 暗赤背景 `rgba(255,0,64,0.25)` + 赤い取り消し線 + 赤glow (`text-shadow: 0 0 8px #ff0040`) + ボーダー + 微かなグリッチ（0.5%確率で点滅）
- **追加（修正テキスト）**: 暗緑背景 `rgba(0,255,65,0.25)` + 明るい緑テキスト + 強い緑glow + ボーダー + box-shadow
- **変更なし**: 通常テキスト

### コメント一覧

- 各コメントアイテムの番号表示を `■` や `▸` などの記号に
- カテゴリタグをシアンアクセントで表示
- before/after のペア表示は、beforeを暗赤、afterを鮮緑で

## 6. Animations & Effects

### フルインパクト（音なし、パフォーマンス優先）

#### 常時エフェクト

1. **CRTスキャンライン**: 全画面に半透明の水平ストライプオーバーレイ
   ```css
   background: repeating-linear-gradient(0deg, rgba(0,255,65,0.03) 0px, rgba(0,255,65,0.03) 1px, transparent 1px, transparent 2px);
   ```
2. **Matrix文字の雨**: canvasで背景にバイナリ文字を落下（パフォーマンス注意、必要に応じて削除）
3. **パネル枠の微細フリッカー**: 0.5%確率でopacityが一瞬変動
4. **下部ステータスバー**: ランダムメッセージが数秒ごとに切り替わる

#### インタラクションエフェクト

5. **ボタンホバー**: glow強化 + 背景の明るさ変化
6. **入力フォーカス**: ボーダーglow + カーソル点滅
7. **タブ切り替え**: 下線のglowフェードイン
8. **サイドバー非アクティブ項目の ○**: ランダムに点滅

#### 校正フロー演出

9. **ブートシーケンス**: アプリ起動時にBIOS風テキストが1行ずつタイプ表示（初回のみ、または設定で制御）
10. **校正リクエスト時**: `[ SCANNING ]` → `[ PARSING ]` → `[ QUERY ]` → `[ RECEIVE ]` → `[ VALIDATE ]` → `[ COMPLETE ]` のステータス行が順に表示
11. **校正完了時**: `ACCESS GRANTED` が一瞬フラッシュ（緑背景→透明へのフェードアウト）
12. **結果表示**: タイプライターエフェクトでテキストが1行ずつ表示される
13. **エラー時**: グリッチ演出（テキストが一瞬水平にズレる）

#### ページ遷移

14. **モジュール切替**: パネルのコンテンツがフェードアウト→フェードイン

#### プログレスバー

15. **脈動glow**: プログレスバーのグリーン→シアンのグラデーション + box-shadowが脈動

### パフォーマンス考慮

- Matrix文字の雨は`requestAnimationFrame`で制御、画面外の文字は描画しない
- スキャンラインはCSS固定（JSなし）
- フリッカーはCSS `animation` + 低頻度（数秒に1回）
- `prefers-reduced-motion`メディアクエリを尊重 — アニメーションを無効化
- 大量テキスト表示時（履歴一覧など）はタイプライターエフェクトをスキップ

### 削除候補（パフォーマンス次第）

- Matrix文字の雨（canvas）— 最も重い、代替はCSS背景
- パネル枠フリッカー — 小さいが不要なら削除
- タイプライターエフェクト — 長文では重い

## 7. Status Messages — ランダムメッセージ

下部システムバーに表示するジョーク/ハッカー風メッセージ。数秒ごとにランダムに切り替わる。

```
"All systems operational."
"Firewall: ACTIVE (localhost only)"
"Coffee level: CRITICAL"
"There is no place like 127.0.0.1"
"Uptime: {n}h {m}m | Sessions: 1"
"Document processed: 0 errors found"
"Remember: with great power comes great responsibility"
"rm -rf /boredom"
"SSH connection secure. Probably."
"AI model loaded. Skynet is not activated."
```

## 8. Boot Sequence — 起動時演出

アプリの初回起動時（またはリロード時）に表示されるブートシーケンス。

```
GOV_ASSIST BIOS v2.0 — POST check...
Memory test... 8192K OK
Loading AI kernel... kimi-k2.5
Connecting to localhost:8000... CONNECTED
Mounting SQLite database... MOUNTED
[ SYSTEM READY ]
Last login: {timestamp} from 127.0.0.1
history records: {n} | db size: {n}MB
▶ GOV_ASSIST v2.0 initialized. Welcome, operator._
```

- 1行ずつタイプアニメーションで表示
- 全体で1-2秒、スキップ可能（クリックまたはキー入力）
- `localStorage` に `boot_shown: true` を保存し、同一センスでは2回目以降スキップ（設定で変更可能）

## 9. Easter Eggs

- コンソールで `sudo` と入力 → "Nice try." メッセージ
- 空の校正を3回連続実行 → "Error 404: Text not found." メッセージ
- 設定ページで特定の操作 → 隠しメッセージ

（実装負荷が低いものを優先、パフォーマンスに影響しない範囲で）

## 10. File Changes

### 変更対象ファイル

| ファイル | 変更内容 |
|----------|---------|
| `frontend/src/css/base.css` | 全トークン値の変更、新規glowトークン追加、フォント定義変更 |
| `frontend/src/css/layout.css` | tmux風パネルレイアウトへの全面書き換え |
| `frontend/src/css/components.css` | 全コンポーネントの色・border-radius・glow変更 |
| `frontend/index.html` | Google Fonts（Share Tech Mono）読み込み追加 |
| `frontend/src/App.jsx` | レイアウト構造の変更（Header→ステータスバー、Sidebar→左パネル） |
| `frontend/src/components/Header.jsx` | ステータスバーコンポーネントに全面改修 |
| `frontend/src/components/SideMenu.jsx` | 左パネルコンポーネントに改修 |
| `frontend/src/components/WarningModal.jsx` | 暗いテーマ対応 |
| `frontend/src/tools/proofreading/ResultView.jsx` | Diff表示のエフェクト追加 |
| `frontend/src/tools/proofreading/DiffView.jsx` | ハイライト/比較のグロー・グリッチ追加 |
| `frontend/src/tools/history/HistoryList.jsx` | 暗いテーマ対応 |
| `frontend/src/tools/history/HistoryDetail.jsx` | 暗いテーマ対応 |
| `frontend/src/tools/settings/Settings.jsx` | 暗いテーマ対応 |

### 新規ファイル

| ファイル | 内容 |
|----------|------|
| `frontend/src/effects/BootSequence.jsx` | ブートシーケンス演出コンポーネント |
| `frontend/src/effects/MatrixRain.jsx` | Matrix文字の雨（canvas）コンポーネント |
| `frontend/src/effects/ScanlineOverlay.jsx` | CRTスキャンラインオーバーレイ |
| `frontend/src/effects/GlitchText.jsx` | グリッチテキストエフェクト |
| `frontend/src/effects/useStatusMessages.js` | ランダムステータスメッセージフック |
| `frontend/src/css/animations.css` | 全アニメーション@keyframes定義 |

### 変更不要

- `frontend/src/api/client.js` — API通信に変更なし
- `frontend/src/utils/storage.js` — localStorage操作に変更なし
- `frontend/src/tools/proofreading/preprocess.js` — テキスト処理ロジックに変更なし
- `frontend/src/tools/proofreading/fileExtractor.js` — ファイル抽出に変更なし
- バックエンド全体 — フロントエンドのみの変更

## 11. Non-functional Requirements

- `prefers-reduced-motion` を尊重し、アニメーションを無効化するオプションを提供
- フォントの読み込みは `font-display: swap` でFOITを防止
- canvasアニメーションは`requestAnimationFrame`で制御し、タブ非表示時は停止
- 既存のテストはトークン値の変更により色のassertが失敗する可能性があるため、テストの更新も必要
- 日本語テキストの可読性を確保するため、校正結果本文にはglowを適用しない
