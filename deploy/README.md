# Nigehban — Oracle Cloud / self-hosted deployment

## Stack on one VM

- Docker Compose: Postgres, Redis, MinIO
- Ollama (host or container with profile)
- FastAPI (`uvicorn app.main:app --host 0.0.0.0 --port 8000`)
- Next.js standalone (`node apps/web/server.js`)
- Caddy for TLS reverse proxy

## Quick start

```bash
docker compose up -d postgres redis minio minio-init
docker compose --profile ollama up -d ollama
cd apps/api && alembic upgrade head && python scripts/seed_all.py
uvicorn app.main:app --host 0.0.0.0 --port 8000
python -m app.workers.runner   # or set WORKER_INLINE=true
cd apps/web && pnpm build && pnpm start
caddy run --config deploy/Caddyfile
```

## Environment

Copy `.env.example` to `.env` and set:

- `LLM_PROVIDER=ollama`
- `OLLAMA_BASE_URL=http://127.0.0.1:11434`
- `DATABASE_URL`, `REDIS_URL`, `S3_*` for MinIO

## Backups

Run `deploy/backup.sh` daily via cron — dumps Postgres to MinIO bucket `backups`.

## Firewall

Allow only 80/443 publicly; bind Postgres/Redis to localhost.
