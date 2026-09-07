#!/usr/bin/env bash
# Daily PostgreSQL backup to MinIO (configure mc alias first)
set -euo pipefail
STAMP=$(date +%Y%m%d_%H%M%S)
FILE="/tmp/nigehban_${STAMP}.sql.gz"
docker compose exec -T postgres pg_dump -U nigehban nigehban | gzip > "$FILE"
mc cp "$FILE" local/nigehban-media/backups/
rm -f "$FILE"
echo "Backup uploaded: nigehban_${STAMP}.sql.gz"
