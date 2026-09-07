#!/usr/bin/env bash
# Seed scam patterns, curated references, and claims
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/apps/api"
python scripts/seed_all.py
