---
kind: dependency_management
name: Monorepo Dependency Management via pnpm Workspaces + Turbo + Hatchling
category: dependency_management
scope:
    - '**'
source_files:
    - package.json
    - pnpm-workspace.yaml
    - turbo.json
    - apps/web/package.json
    - apps/api/pyproject.toml
    - bun.lock
---

## Overview

This repository is a Python/Node.js monorepo that manages dependencies through two parallel systems: **pnpm workspaces** for the JavaScript/TypeScript side and **Hatchling (PEP 517) with `pyproject.toml`** for the Python API. A root-level `package.json` declares workspace membership, while each sub-project declares its own dependencies.

## JavaScript/TypeScript Dependencies

- **Package manager**: `pnpm` — evidenced by the presence of `pnpm-workspace.yaml`, a root `bun.lock` lockfile (likely from an earlier switch), and workspace configuration.
- **Workspace layout** (`pnpm-workspace.yaml`): Declares two workspace roots:
  - `apps/*` — contains `apps/web` (Next.js frontend)
  - `packages/*` — reserved for shared packages (`shared-types`, `ui`, `config-tailwind`, `config-typescript`; currently placeholder directories with `.gitkeep`)
- **Root `package.json`**:
  - Declares `workspaces: ["apps/*", "packages/*"]`
  - Installs only monorepo tooling as devDependencies: `turbo ^2.3.3`, `prettier ^3.4.2`, `typescript ^5.7.2`
  - Exposes top-level scripts (`dev`, `build`, `lint`, `typecheck`, `clean`, `format`) that delegate to Turbo.
- **App-level dependencies** (`apps/web/package.json`):
  - Frontend runtime deps include Next.js 14, React 18, Radix UI, Framer Motion, Three.js ecosystem, TanStack Query, Zustand, Tailwind CSS, etc.
  - Dev deps include TypeScript, ESLint, PostCSS/Autoprefixer, and type definitions.
- **Build orchestration** (`turbo.json`):
  - Defines tasks `build`, `dev`, `lint`, `typecheck`, `clean` with caching rules and dependency ordering (`dependsOn: ["^build"]`).
  - Global cache invalidation keys on `.env.*local` and `.env` files.
- **Lockfile**: A root `bun.lock` exists, suggesting the repo may have previously used Bun or was migrated; pnpm is configured but no `pnpm-lock.yaml` is visible in the tree.
- **Private registry / vendoring**: No `.npmrc`, `.pnp*.cjs`, or `vendor/` directory is present. No private registry URL is configured at the workspace level. Shared packages under `packages/` are not yet published — they exist as local workspace placeholders.

## Python Dependencies

- **Dependency manifest**: `apps/api/pyproject.toml` uses PEP 621 metadata with `hatchling` as the build backend (`[build-system] requires = ["hatchling.build"]`).
- **Declared dependencies** include FastAPI, Uvicorn, SQLAlchemy 2+, asyncpg, Alembic, Anthropic SDK, Celery with Redis, Pydantic Settings, pgvector, python-jose, Passlib, Pillow, and pytesseract.
- **Python version constraint**: `requires-python = ">=3.12"`.
- **No virtual environment or lockfile** (e.g., `requirements.txt`, `poetry.lock`, `uv.lock`, `pip-tools`) is committed to the repo — dependencies are declared declaratively in `pyproject.toml` and resolved at install time.
- **No vendored third-party code** under `apps/api/`; all imports resolve to installed packages.

## Conventions Observed

1. **Monorepo-first**: All apps and shared packages live under `apps/` and `packages/` and are hoisted into a single pnpm workspace.
2. **Task orchestration via Turbo**: Every app exposes `dev`, `build`, `lint`, `typecheck` scripts consumed by the root `turbo` commands.
3. **Shared package scaffolding**: The `packages/` directory is pre-structured for future internal packages (`shared-types`, `ui`, `config-tailwind`, `config-typescript`), though none contain source code yet.
4. **Declarative Python deps**: Python dependencies are pinned via caret/greater-than-or-equal ranges in `pyproject.toml` rather than exact pins in a lockfile.
5. **Docker-based deployment**: `apps/api/Dockerfile` and `docker-compose.yml` imply containerized builds that will resolve dependencies at image build time using the manifests above.