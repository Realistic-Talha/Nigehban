"""Pytest configuration and default test environment."""

import os

os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("SEARCH_PROVIDER", "mock")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://nigehban:nigehban@localhost:5432/nigehban",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("WORKER_INLINE", "false")
