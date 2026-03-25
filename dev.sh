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
