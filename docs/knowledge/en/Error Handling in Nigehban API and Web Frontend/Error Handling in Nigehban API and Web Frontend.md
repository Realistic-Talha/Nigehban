---
kind: error_handling
name: Error Handling in Nigehban API and Web Frontend
category: error_handling
scope:
    - '**'
source_files:
    - apps/api/app/main.py
    - apps/api/app/agents/base.py
    - apps/api/app/api/v1/router.py
    - apps/api/app/api/v1/checks.py
    - apps/api/app/api/v1/mediacheck.py
    - apps/api/app/utils/rate_limiter.py
    - apps/api/app/core/security.py
    - apps/api/app/schemas/responses.py
    - apps/web/src/lib/api-client.ts
---

## Overview

The Nigehban monorepo uses a layered error-handling approach: FastAPI `HTTPException` for API-layer errors, structured agent-level graceful degradation for AI pipeline failures, a custom `ApiError` class on the frontend, and middleware/dependency-based rate limiting. There is no centralized exception-to-HTTP mapping or global exception handler registered in `main.py`; instead, each layer handles its own concerns.

## Backend (FastAPI)

### API-layer errors
- Errors are raised as `fastapi.HTTPException` with explicit `status_code` values from `fastapi.status`. Examples:
  - `404 Not Found` when a check record is missing (`apps/api/app/api/v1/checks.py`).
  - `422 Unprocessable Entity` for invalid uploads / oversized files (`apps/api/app/api/v1/mediacheck.py`).
  - `413 Request Entity Too Large` for oversized media payloads.
  - `201 Created` for successful report creation; `202 Accepted` for async submission endpoints.
- The `/health` endpoint returns a plain dict `{"status": "ok"}` — no error response path exists there.
- Webhook handlers return raw `Response(status_code=...)` directly (e.g. `403 Forbidden` for bad verify tokens in `apps/api/app/api/webhooks/whatsapp.py`).

### Rate limiting as error source
- Two implementations exist:
  - `RateLimiter` dependency in `apps/api/app/utils/rate_limiter.py` raises `HTTPException(429)` per request via FastAPI `Depends`.
  - `RateLimitMiddleware` in `apps/api/app/core/security.py` is a Starlette `BaseHTTPMiddleware` that returns a `JSONResponse(429)` before calling the next handler.
- Both use an in-memory sliding window keyed by `request.client.host`, with a comment noting Redis-backed replacement for production multi-instance deployments.

### Agent pipeline errors (graceful degradation)
- `BaseAgent.execute()` in `apps/api/app/agents/base.py` wraps every agent's `run()` in `asyncio.wait_for` with a configurable timeout.
- On `asyncio.TimeoutError` or any other `Exception`, the agent:
  1. Logs the failure at `ERROR` level (`logger.exception`).
  2. Publishes a `PipelineEvent` with `status="error"` to Redis Pub/Sub channel `pipeline:{check_id}` so SSE consumers see the failure.
  3. Returns a normalized result dict with `_meta.status = "error"`, `confidence = 0.0`, and `output.error` set to a message like `<ExceptionType>: <message>`.
- This pattern lets individual agents fail without crashing the whole pipeline; orchestrators can aggregate partial results.
- Individual agent modules (factcheck, mediacheck) also wrap LLM calls in `try/except Exception` blocks and fall back to empty outputs rather than propagating exceptions upward.

### External service errors
- LLM service (`apps/api/app/services/llm.py`) inspects `exc.status_code` to decide whether to re-raise or treat as a client-side error.
- WhatsApp service (`apps/api/app/services/whatsapp.py`) catches HTTP errors and returns `{"error": status_code, "detail": response_text}`.

## Frontend (Next.js / TypeScript)

- `apps/web/src/lib/api-client.ts` defines a custom `ApiError extends Error` with a `status: number` field.
- The shared `fetchApi<T>()` helper throws `ApiError(message, res.status)` whenever `res.ok` is false, extracting `body.detail` if present.
- Upload-style helpers (`submitScamCheck`, `submitMediaCheck`) call `fetch` directly and `.then(r => r.json())`, which means they do **not** throw on non-2xx responses — callers must handle them differently.
- All typed API functions (`getFeed`, `submitFactCheck`, `getCheck`, `searchScams`, dashboard helpers) go through `fetchApi`, so callers receive a uniform `ApiError` with a numeric status code.

## Conventions observed

| Area | Convention | Evidence |
|---|---|---|
| API errors | Raise `HTTPException` with explicit `status_code` constants from `fastapi.status` | `checks.py`, `mediacheck.py` |
| Async submissions | Return `202 Accepted` to signal background processing | `factcheck.py`, `scamcheck.py`, `mediacheck.py` |
| Validation errors | Use `422 Unprocessable Entity` for malformed requests/files | `mediacheck.py` |
| Agent failures | Catch all exceptions inside `BaseAgent.execute`, publish SSE `error` event, return normalized error payload | `agents/base.py` |
| Non-fatal side effects | Wrap Redis pub/sub in try/except and log warnings instead of failing the pipeline | `agents/base.py:_publish_status` |
| Rate limiting | Provide both dependency and middleware variants returning `429` | `utils/rate_limiter.py`, `core/security.py` |
| Frontend errors | Centralized `ApiError` thrown from `fetchApi` with `status` and `detail` extraction | `web/src/lib/api-client.ts` |
| File uploads | Bypass `fetchApi` and handle responses inline in component code | `web/src/lib/api-client.ts` upload helpers |

## Gaps / notes

- No global exception handler is registered in `main.py`; FastAPI's default exception handling is relied upon to convert `HTTPException` into JSON responses.
- There is no shared domain-specific exception type (e.g. `NotFoundError`, `ValidationError`) — all API errors are `HTTPException` instances.
- The two rate-limiting implementations serve different purposes (dependency vs middleware) but share the same in-memory strategy; only one would be active at runtime.