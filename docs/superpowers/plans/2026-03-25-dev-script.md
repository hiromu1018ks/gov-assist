# dev.sh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** プロジェクトルートに `dev.sh` を配置し、1コマンドでbackendとfrontendをtmux左右分割ペインで起動できるようにする。

**Architecture:** 純粋なbashスクリプト。tmuxセッション `gov-assist` を作成し、左ペインにuvicorn、右ペインにViteを起動する。事前チェックでtmuxの存在とディレクトリ構造を検証する。

**Tech Stack:** bash, tmux

---

### Task 1: dev.sh スクリプト作成

**Files:**
- Create: `dev.sh`

- [ ] **Step 1: dev.sh を作成する**

```bash
#!/usr/bin/env bash
set -euo pipefail

SESSION="gov-assist"

# tmux check
if ! command -v tmux &>/dev/null; then
  echo "Error: tmux is not installed." >&2
  echo "Install with: sudo pacman -S tmux  (Arch) / sudo apt install tmux  (Ubuntu)" >&2
  exit 1
fi

# directory check
if [ ! -d "backend" ]; then
  echo "Error: backend/ directory not found. Run from project root." >&2
  exit 1
fi

if [ ! -f "frontend/package.json" ]; then
  echo "Error: frontend/package.json not found. Run from project root." >&2
  exit 1
fi

# attach if session already exists
if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "Attaching to existing session: $SESSION"
  exec tmux attach -t "$SESSION"
fi

# create session with backend in left pane
tmux new-session -d -s "$SESSION" -c backend -n dev

# split right, run frontend
tmux split-window -h -t "$SESSION:dev" -c frontend
tmux send-keys -t "$SESSION:dev.1" "npm run dev" Enter

# start backend in left pane
tmux send-keys -t "$SESSION:dev.0" "uvicorn main:app --reload" Enter

# focus left pane
tmux select-pane -t "$SESSION:dev.0"

# attach
exec tmux attach -t "$SESSION"
```

- [ ] **Step 2: 実行権限を付与する**

Run: `chmod +x dev.sh`

- [ ] **Step 3: 動作確認 — ヘルプテスト（tmuxなし環境のエラー表示）**

Run: `bash -c 'PATH=/dev/null ./dev.sh'` (tmuxを一時的に見えなくして実行)
Expected: "Error: tmux is not installed." のメッセージ

- [ ] **Step 4: 動作確認 — スクリプト構文チェック**

Run: `bash -n dev.sh`
Expected: 出力なし（構文エラーなし）

- [ ] **Step 5: Commit**

```bash
git add dev.sh
git commit -m "feat: add dev.sh for one-command dev server startup via tmux"
```
