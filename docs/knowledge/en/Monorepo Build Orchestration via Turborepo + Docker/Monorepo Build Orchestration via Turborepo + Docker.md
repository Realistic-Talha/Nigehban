---
kind: build_system
name: Monorepo Build Orchestration via Turborepo + Docker
category: build_system
scope:
    - '**'
source_files:
    - turbo.json
    - package.json
    - pnpm-workspace.yaml
    - apps/api/pyproject.toml
    - apps/api/Dockerfile
    - apps/web/package.json
    - docker-compose.yml
---

## Build System Overview

Nigehban is a Python/Next.js monorepo built with **Turborepo** as the top-level orchestrator, **pnpm workspaces** for package resolution, and **Docker** (multi-stage) for containerizing the FastAPI backend. The Python API uses **uv** for dependency installation and **Hatchling** as its build backend.

## Key Files and Packages

- `turbo.json` — defines tasks (`build`, `dev`, `lint`, `typecheck`, `clean`) and caching rules; `build` depends on upstream dependencies (`^build`) and emits `.next/**` and `dist/**`.
- `package.json` (root) — declares workspace roots `apps/*` and `packages/*`; exposes `dev`, `build`, `lint`, `typecheck`, `clean`, `format` scripts that delegate to Turbo.
- `pnpm-workspace.yaml` — mirrors the root workspaces config for pnpm.
- `apps/api/pyproject.toml` — Python project manifest using Hatchling (`hatchling.build`), requires Python ≥3.12, pins FastAPI, SQLAlchemy, Celery, Anthropic, pgvector, etc.
- `apps/api/Dockerfile` — two-stage build: `builder` stage installs system deps (`build-essential`, `libpq-dev`, `tesseract-ocr`), copies `pyproject.toml`, runs `uv venv` + `uv pip install --no-cache-dir .`; `runtime` stage copies only the virtualenv and app code.
- `docker-compose.yml` — local dev stack with `postgres` (`pgvector/pg16`) and `redis` services, named volumes, healthchecks, and port mappings.
- `apps/web/package.json` — Next.js app with standard `dev`/`build`/`start`/`lint`/`typecheck` scripts consumed by Turbo.
- `packages/` — placeholder packages (`config-tailwind`, `config-typescript`, `shared-types`, `ui`) declared in workspaces but currently empty (`.gitkeep`).

## Architecture and Conventions

### Monorepo layout
- `apps/` holds deployable applications (`api` = FastAPI, `web` = Next.js).
- `packages/` is reserved for shared libraries consumed by apps (currently stubs).
- Root `package.json` is the single entry point for all cross-app commands via `turbo <task>`.

### Task graph
- `turbo build` triggers each app's `build` script; `dependsOn: ["^build"]` ensures shared packages are built before consumers.
- `dev` is marked `persistent: true` and uncached so hot-reload works across apps.
- `globalDependencies` include `**/.env.*local` and `**/.env` so env changes invalidate caches.

### Python API build
- Uses **uv** (Astral) for fast venv creation and pip installation inside the Docker builder stage.
- Dependencies are installed from `.` (the `apps/api` directory) so `pyproject.toml` is the source of truth.
- Runtime image strips build-only tools, keeping only `libpq5` and `tesseract-ocr` as runtime system deps.
- Entrypoint: `uvicorn app.main:app --host 0.0.0.0 --port 8000`.

### Frontend build
- Next.js builds produce `.next/` output, which Turbo marks as an artifact.
- TypeScript typechecking (`tsc --noEmit`) is a separate task wired through Turbo.

### Local development
- `docker-compose.yml` provisions Postgres (with pgvector extension) and Redis as persistent services.
- Apps are run via `turbo dev` (which starts both `apps/api` and `apps/web` concurrently).

## Conventions and Constraints

- All cross-app commands go through the root `package.json` scripts; direct invocation of per-app tooling is bypassed in favor of Turbo orchestration.
- Environment files are treated as global build inputs — any change to `.env` or `.env.local` forces cache invalidation across tasks.
- Python packaging uses PEP 621 metadata in `pyproject.toml` with Hatchling; no `setup.py` exists.
- Docker images follow a multi-stage pattern separating build-time and runtime dependencies to minimize image size.
- Shared packages under `packages/` must be published/imported as workspace references rather than path imports, since Turbo resolves them through pnpm workspaces.
- No CI pipeline or release automation was found in this branch; build and deployment are driven locally via Docker Compose and Dockerfiles.