---
kind: configuration_system
name: Pydantic Settings-Based Environment Configuration with Docker/Compose Integration
category: configuration_system
scope:
    - '**'
source_files:
    - apps/api/app/core/config.py
    - .env.example
    - apps/api/app/core/database.py
    - apps/api/app/core/redis.py
    - apps/api/app/workers/celery_config.py
    - docker-compose.yml
    - turbo.json
    - apps/web/next.config.ts
    - apps/api/pyproject.toml
---

## What system/approach is used

The Nigehban monorepo uses **pydantic-settings** (`BaseSettings`) as the central configuration loader for the Python API. A single `Settings` class in `apps/api/app/core/config.py` declares every runtime setting with type annotations, defaults, and environment variable names. The settings module is configured to read from a `.env` file (UTF-8 encoded) and ignores unknown env vars (`extra="ignore"`).

The web frontend (Next.js under `apps/web`) relies on Next.js's built-in environment variable handling — it reads `process.env.NODE_ENV` at build time and exposes client-side variables via the `NEXT_PUBLIC_` prefix convention.

Docker Compose (`docker-compose.yml`) provisions infrastructure services (PostgreSQL + pgvector, Redis) and injects their credentials via the `environment:` block, which are consumed by the API through the same env var contract defined in `config.py`.

Build orchestration is handled by Turborepo (`turbo.json`), which declares global dependencies on `**/.env.*local` and `**/.env`, ensuring that any change to environment files invalidates caches across all workspace packages.

## Key files and packages

- `apps/api/app/core/config.py` — Central `Settings(BaseSettings)` model; defines all env-backed config keys and defaults.
- `apps/api/app/core/database.py` — Async SQLAlchemy engine/session factory consuming `settings.DATABASE_URL`; toggles SQL echo based on `settings.ENVIRONMENT`.
- `apps/api/app/core/redis.py` — Async Redis connection pool wrapper consuming `settings.REDIS_URL`.
- `apps/api/app/workers/celery_config.py` — Celery app initialized with broker/backend URLs from `settings.REDIS_URL`; defines task queues and worker concurrency limits.
- `.env.example` — Template of all required environment variables (database, Redis, Anthropic, WhatsApp, search API, Cloudflare R2/S3, CORS origins, `NEXT_PUBLIC_API_URL`).
- `docker-compose.yml` — Defines postgres and redis services with hardcoded credentials; healthchecks ensure readiness before dependents start.
- `turbo.json` — Declares `globalDependencies` on `.env*` files so env changes invalidate the Turborepo cache.
- `apps/web/next.config.ts` — Uses `process.env.NODE_ENV` to conditionally strip console output in production builds.
- `apps/api/pyproject.toml` — Declares `pydantic-settings` as a dependency and pins FastAPI, async SQLAlchemy, Celery+Redis, Anthropic SDK, etc.

## Architecture and conventions

1. **Single source of truth**: All API configuration flows through one `settings = Settings()` singleton imported wherever needed (database, redis, celery, storage, services). There is no per-module config loading.

2. **Environment-first, defaults-safe**: Every setting has a sensible default in the `Settings` class (e.g. `DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/nigehban`, `REDIS_URL=redis://localhost:6379/0`, `LOCAL_STORAGE_DIR="uploads"`). This allows the app to start locally without explicit env vars while still being fully overridable.

3. **Typed configuration**: Pydantic enforces types at import time — e.g. `CORS_ORIGINS: list[str]`, `RSS_FEED_URLS: list[str]`. Invalid values raise validation errors early during application startup rather than at request time.

4. **Secrets live only in env**: Secrets (API keys, tokens, DB passwords) are never committed to code. `.env.example` documents the shape but contains placeholder values. The root `.gitignore` excludes `.env`.

5. **Infrastructure config separated from app config**: `docker-compose.yml` hardcodes service credentials (e.g. `POSTGRES_USER`, `POSTGRES_PASSWORD`) for local development. Production deployments would override these via platform-specific secret management, since the API reads them purely from env vars.

6. **Feature/service toggling via env**: `ENVIRONMENT` controls behavior such as whether SQLAlchemy echoes SQL queries (`echo=settings.ENVIRONMENT == "dev"`). Storage backends are selected by presence of R2 vs generic S3 env vars.

7. **Turborepo env awareness**: `turbo.json` lists `**/.env.*local` and `**/.env` as `globalDependencies`, so changing environment variables triggers rebuilds across the monorepo.

## Conventions and constraints

- **Naming convention**: Env var names match the uppercase attribute names on the `Settings` class exactly (e.g. `DATABASE_URL`, `REDIS_URL`, `ANTHROPIC_API_KEY`, `WHATSAPP_TOKEN`, `R2_ACCOUNT_ID`, `S3_ENDPOINT`). New settings must be added as attributes on `Settings` to be discoverable.
- **No nested config objects**: All configuration is flat key-value pairs loaded into a single Pydantic model; there is no hierarchical YAML/JSON config file format.
- **Defaults must be provided**: Every field in `Settings` has a default value, allowing the app to run in minimal environments. Omitting a required secret will result in an empty string or default, not a missing-key error (except where downstream code validates).
- **Client-facing variables use `NEXT_PUBLIC_` prefix**: The example shows `NEXT_PUBLIC_API_URL`, following Next.js convention for exposing env vars to the browser bundle.
- **Celery reuses the same Redis URL**: Both the API's async Redis client and Celery's broker/backend share `settings.REDIS_URL`, avoiding duplicated connection strings.
- **Docker Compose credentials are development-only**: The compose file embeds plaintext credentials intended for local dev; production should replace these with platform secrets injected as env vars.