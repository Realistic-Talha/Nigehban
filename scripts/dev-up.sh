#!/usr/bin/env bash
# Bootstrap local zero-cost dev stack for Nigehban
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Starting Docker services (postgres, redis, minio)..."
docker compose up -d postgres redis minio minio-init

echo "==> Waiting for Postgres..."
until docker compose exec -T postgres pg_isready -U nigehban >/dev/null 2>&1; do
  sleep 1
done

if docker compose --profile ollama ps ollama 2>/dev/null | grep -q Up; then
  echo "==> Ollama is running — pulling models (may take a while)..."
  docker compose exec -T ollama ollama pull qwen2.5:7b-instruct || true
  docker compose exec -T ollama ollama pull qwen2.5:14b-instruct || true
else
  echo "==> Tip: start Ollama with: docker compose --profile ollama up -d ollama"
fi

echo "==> Running Alembic migrations..."
cd apps/api
if command -v uv >/dev/null 2>&1; then
  uv run alembic upgrade head
  uv run python scripts/seed_all.py || true
else
  alembic upgrade head
  python scripts/seed_all.py || true
fi

echo "==> Done. Start API: cd apps/api && uvicorn app.main:app --reload --port 8000"
