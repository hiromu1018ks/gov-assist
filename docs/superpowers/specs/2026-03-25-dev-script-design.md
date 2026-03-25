# dev.sh: 一発起動スクリプト設計

## 概要

プロジェクトルートに `dev.sh` を配置し、1コマンドでbackend（uvicorn）とfrontend（Vite）をtmuxの左右分割ペインで起動する。

## 背景

現在の開発環境では、backendとfrontendを別々のターミナルで起動する必要がある。これを `./dev.sh` 一発で起動し、tmuxの左右分割ペインで両方のログをリアルタイムに確認できるようにする。

## アプローチ

純粋なbashスクリプト。tmux以外の追加依存なし。

## スクリプト構成

```
dev.sh
├── 事前チェック（tmux、ディレクトリ）
├── tmuxセッション作成（名前: gov-assist）
│   ├── 左ペイン = backend (uvicorn main:app --reload)
│   └── 右ペイン = frontend (npm run dev)
└── セッションにアタッチ
```

## 振る舞い

### 起動時

1. `tmux` がインストールされているかチェック → なければエラーで終了
2. `backend/` ディレクトリと `frontend/package.json` が存在するかチェック → なければエラーで終了
3. `gov-assist` という名前のtmuxセッションの存在確認:
   - 存在する → `tmux attach -t gov-assist` して終了（二重起動防止）
   - 存在しない → 新規セッションを作成
4. 新規セッション作成:
   - `tmux new-session -d -s gov-assist -c backend` → 左ペインでuvicorn起動
   - ペインを左右に分割
   - 右ペインの作業ディレクトリを `frontend/` に変更 → `npm run dev` 起動
   - 左ペインにフォーカスを戻す
5. `tmux attach -t gov-assist` でアタッチ

### 終了時

- `Ctrl+B, X` でいずれかのペインを閉じるとプロセスも終了
- セッション全体を閉じる: デタッチ（`Ctrl+B, D`）後 `tmux kill-session -t gov-assist`

### エラーハンドリング

- tmux未インストール: インストール方法を案内して `exit 1`
- backend/frontend ディレクトリ不存在: メッセージ表示して `exit 1`

## 使い方

```bash
./dev.sh                    # 起動
Ctrl+B, D                   # デタッチ
tmux attach -t gov-assist   # 再接続
tmux kill-session -t gov-assist  # セッション終了
```

## ファイル

- `dev.sh` — プロジェクトルートに配置、実行権限付き
