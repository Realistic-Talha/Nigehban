---
kind: logging_system
name: Python Standard Library `logging` with Per-Module Loggers and Alembic File-Based Config
category: logging_system
scope:
    - '**'
source_files:
    - apps/api/app/agents/base.py
    - apps/api/app/agents/orchestrator.py
    - apps/api/app/agents/factcheck/claim_extraction.py
    - apps/api/app/agents/factcheck/verdict_synthesis.py
    - apps/api/app/agents/mediacheck/audio_sync.py
    - apps/api/app/agents/mediacheck/metadata_extract.py
    - apps/api/app/agents/mediacheck/reverse_search.py
    - apps/api/app/agents/mediacheck/visual_analysis.py
    - apps/api/alembic/env.py
    - apps/api/alembic.ini
---

## What system/approach is used

The Nigehban API uses Python's built-in `logging` module (stdlib) — no third-party logging framework (e.g. structlog, loguru, python-json-logger) is imported anywhere in the codebase. Each module that needs to emit logs creates a logger via `logger = logging.getLogger(__name__)`, which gives each file its own fully-qualified logger name under the `app.*` package hierarchy. There is **no centralized logger factory or root logger configuration** in the FastAPI application entry point (`apps/api/app/main.py`); the root logger is left at its default level.

Alembic migrations configure their own logging separately via an `alembic.ini` file using `logging.config.fileConfig`, routing output to `sys.stderr` with a `StreamHandler` and a simple `%(levelname)-5.5s [%(name)s] %(message)s` formatter.

## Key files and packages

- `apps/api/app/agents/base.py` — defines the shared `BaseAgent.execute()` wrapper that emits `info` on start/completion, `error` on timeout/failure, and `warning` when Redis Pub/Sub publishing fails; this is the single place where agent lifecycle timing and status are logged.
- `apps/api/app/agents/orchestrator.py` — logs pipeline routing decisions and per-agent orchestration steps.
- `apps/api/app/agents/factcheck/*.py` and `apps/api/app/agents/mediacheck/*.py` — each agent module declares its own `logger = logging.getLogger(__name__)` and emits `info`/`warning`/`error` messages for LLM call outcomes, empty inputs, and JSON-parse failures.
- `apps/api/alembic/env.py` — calls `logging.config.fileConfig(config.config_file_name)` so Alembic inherits the file-based config.
- `apps/api/alembic.ini` — the only explicit logging configuration in the repo: sets root level to `WARN`, SQLAlchemy engine to `WARN`, Alembic to `INFO`, handler to `stderr`, and a generic console formatter.
- `tooling/scripts/seed.py` — uses plain `print(...)` for CLI progress output (not part of the runtime logging system).

## Architecture and conventions

1. **Per-module logger instance**: Every agent module follows the pattern `import logging` then `logger = logging.getLogger(__name__)`. This produces names like `app.agents.factcheck.claim_extraction`, enabling fine-grained filtering by package.
2. **Structured-ish message fields via positional formatting**: Messages embed contextual keys as literal text segments separated by `|`, e.g. `"Agent '%s' started | check=%s"`, `"Agent '%s' completed in %d ms | confidence=%.1f"`, `"Failed to publish status to %s (agent=%s, status=%s)"`. These are not machine-parsed structured logs — they are human-readable strings designed to be grepped by field name (`check=`, `agent=`, `status=`).
3. **Log levels are used consistently by semantic role**:
   - `info` — normal lifecycle events (agent start/end, orchestrator routing, successful LLM responses).
   - `warning` — recoverable anomalies (empty input, non-JSON LLM response, unknown route, missing media URL).
   - `error` — failure conditions (timeout, evidence retrieval failure, cross-reference failure).
   - `exception` — used once in `BaseAgent.execute` to log the full traceback alongside the error message.
4. **No request-level correlation IDs**: The only cross-cutting identifier injected into log lines is `parent_check_id` (a UUID passed through the agent pipeline), appearing in `_meta` dicts returned from agents and in log messages like `"Agent '%s' started | check=%s"`.
5. **No global log level configuration at app startup**: `main.py` does not call `logging.basicConfig`, `logging.getLogger().setLevel(...)`, or install any handlers. Runtime log verbosity therefore depends entirely on environment defaults plus the Alembic-specific `alembic.ini` fileConfig.
6. **Frontend/web side**: The Next.js frontend (`apps/web/`) contains no server-side logging code; client-side diagnostics would use browser console, which is outside the scope of this backend-focused logging system.

## Conventions and constraints

- **Observed convention (not enforced by code)**: every new agent or service module should create a module-level `logger = logging.getLogger(__name__)` rather than calling `logging.info(...)` directly.
- **Message format convention**: contextual identifiers are embedded inline with `|` separators and `key=value` pairs so logs remain grep-friendly without requiring a structured-log parser.
- **Constraint enforced by implementation**: `BaseAgent._publish_status` wraps Redis Pub/Sub publishing in a try/except that catches all exceptions and logs them as `warning` with `exc_info=True`; this ensures a failed status broadcast never crashes the agent pipeline — a deliberate resilience rule.
- **Alembic logging is isolated**: migration tooling reads its own `alembic.ini` via `fileConfig`, keeping migration output separate from the running API process.
- **No structured/log-as-JSON output, no sinks beyond stderr/console**: there is no configuration for file rotation, syslog, cloud log aggregation, or JSON-formatted output; logs are intended for local/stderr consumption.