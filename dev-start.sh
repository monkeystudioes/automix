#!/usr/bin/env bash
# Quick dev startup without Docker.
# Prerequisites: pip install -r backend/requirements.txt, Redis running locally.

set -e
cd "$(dirname "$0")"

echo "→ Checking Redis..."
redis-cli ping 2>/dev/null || (echo "⚠  Redis not running. Start with: brew services start redis" && exit 1)

export REDIS_URL="redis://localhost:6379"
export UPLOADS_DIR="$(pwd)/uploads"
export OUTPUTS_DIR="$(pwd)/outputs"
mkdir -p uploads outputs

echo "→ Starting Celery worker..."
cd backend
celery -A worker worker --loglevel=info --concurrency=2 &
CELERY_PID=$!

echo "→ Starting FastAPI..."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

echo ""
echo "✓ AutoMix running:"
echo "  API:      http://localhost:8000"
echo "  Frontend: http://localhost:8000  (served from /frontend)"
echo ""
echo "Press Ctrl+C to stop."

cleanup() {
  kill $CELERY_PID $API_PID 2>/dev/null
  echo "Stopped."
}
trap cleanup INT TERM
wait
