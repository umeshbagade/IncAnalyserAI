#!/usr/bin/env bash
#
# start-backend.sh — Build the vector DB, then start the IncAnalyserAI backend.
#
# Usage:
#   ./start-backend.sh                 # build vector DB (if missing) + start server
#   REBUILD_VECTOR_DB=1 ./start-backend.sh   # force a fresh vector DB rebuild
#   SKIP_VECTOR_DB=1 ./start-backend.sh      # skip the vector DB build entirely
#   ./start-backend.sh --no-reload     # start server without --reload
#
set -euo pipefail

# Resolve the directory this script lives in (repo root), regardless of CWD.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
VENV_DIR="$BACKEND_DIR/venv"
VECTOR_STORE_DIR="$BACKEND_DIR/vector_db/vector_store"

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
RELOAD_FLAG="--reload"
[[ "${1:-}" == "--no-reload" ]] && RELOAD_FLAG=""

echo "==> IncAnalyserAI backend startup"
echo "    Repo root : $ROOT_DIR"

# 1) Activate the Python virtual environment.
if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
  echo "ERROR: virtualenv not found at $VENV_DIR"
  echo "       Create it first:  cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
echo "    Python    : $(python3 --version) ($(command -v python3))"

cd "$BACKEND_DIR"

# 2) Build the vector DB before starting the server.
if [[ "${SKIP_VECTOR_DB:-0}" == "1" ]]; then
  echo "==> Skipping vector DB build (SKIP_VECTOR_DB=1)"
elif [[ "${REBUILD_VECTOR_DB:-0}" == "1" || ! -f "$VECTOR_STORE_DIR/chroma.sqlite3" ]]; then
  if [[ "${REBUILD_VECTOR_DB:-0}" == "1" ]]; then
    echo "==> Rebuilding vector DB (REBUILD_VECTOR_DB=1)..."
  else
    echo "==> Vector DB not found — building it now..."
  fi
  python3 vector_db/create_vector_db.py
  echo "==> Vector DB build complete."
else
  echo "==> Vector DB already present at $VECTOR_STORE_DIR (set REBUILD_VECTOR_DB=1 to rebuild)."
fi

# 3) Start the FastAPI server.
echo "==> Starting backend on http://$HOST:$PORT  (docs: http://localhost:$PORT/docs)"
exec uvicorn app.main:app --host "$HOST" --port "$PORT" $RELOAD_FLAG
