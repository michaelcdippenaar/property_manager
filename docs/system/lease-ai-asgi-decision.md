# ADR — Lease AI v2 SSE Runtime Strategy

| Field | Value |
|---|---|
| **Status** | Proposed — needs MC sign-off before Phase 1 |
| **Date** | 2026-05-12 |
| **Decision** | Reuse the existing daphne ASGI runtime; fix the Caddy proxy so SSE flushes; do **not** migrate or split. |
| **Author** | CTO agent |
| **Supersedes** | The audit P1 assumption in `docs/system/lease-ai-agent-architecture.md` §10.2 that Klikk runs on sync WSGI workers. That assumption is incorrect for production. |

---

## 1. Context

`docs/system/lease-ai-agent-architecture.md` decision 17 + §10.2 commits the lease-AI v2 endpoint (`POST /api/v1/leases/templates/<id>/ai-chat-v2/`) to **SSE streaming from day one** — token-streamed Drafter output plus per-agent status events. The "feedback as it goes" UX is load-bearing for v2; without it the multi-agent pipeline feels slower than the single-agent v1 because the user sees nothing for the 12–25 s the pipeline runs.

The audit P1 finding flagged a runtime risk: Django sync WSGI workers buffer `StreamingHttpResponse` chunks until the response completes, which would make SSE appear to hang in production even though it works locally on `manage.py runserver`. The audit recommended one of three migration paths (whole-app ASGI, separate FastAPI sub-app, or drop SSE for v1).

### What's actually true today

A grep of the production deployment surfaces two facts that change the question:

1. **`backend/Dockerfile` line 27 is `CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]`.** Production has been running daphne ASGI since the WebSocket / channels work for maintenance + esigning + leases. `config/asgi.py` wires `ProtocolTypeRouter({"http": get_asgi_application(), "websocket": ...})`. The audit's premise — Klikk is on sync gunicorn workers — is wrong.
2. **`deploy/Caddyfile` lines 145–150 proxy `backend:8000` *without* `flush_interval -1`.** Caddy buffers HTTP/1.1 reverse-proxy responses by default. The Volt MCP block at lines 132–141 explicitly sets `flush_interval -1` because the team has hit this before. The same flag is missing on the main backend reverse proxy.

So the SSE-buffering risk is real, but it lives at the **proxy** layer, not at the WSGI/ASGI layer. Migrating Django would solve a problem we don't have; the actual fix is one line in the Caddyfile (scoped to `/api/v1/leases/templates/*/ai-chat-v2/`) plus the per-view ASGI hygiene checks listed in §5.

There is also one Django-side gotcha: `View.dispatch` (DRF's `APIView` subclasses) is sync by default. A `StreamingHttpResponse` from a sync view under daphne works (daphne shims it into an async iterator), but it ties up a sync-to-async thread and serialises with other sync requests on that worker. For the lease-AI endpoint specifically, we want the view to be `async def` so the SSE generator is a native async iterator.

---

## 2. Options considered

### Option A — Migrate the whole Django app to ASGI

**Status:** Already done. Production is daphne. No-op.

This was the audit's recommendation under the assumption Klikk was on sync WSGI. It is the wrong question because the answer is "yes, already".

### Option B — Run the lease-AI endpoint as a separate FastAPI sub-app

Mount FastAPI under `/api/v1/leases/ai-chat-v2/` via `Starlette.routes` or a sub-mounted ASGI app, served on a separate process or co-located with daphne via a router. Smaller blast radius if the existing Django middleware is a concern.

**Cost:** dual auth stacks (FastAPI doesn't share Django's JWT auth / DRF permissions / agency-tenancy middleware), dual logging, dual Sentry, dual settings. Re-implementing the agency-scoping middleware in FastAPI is a footgun: most v2 features will need to know `current_agency_id()`, which today lives in `apps.accounts.tenancy`. Splitting the stack to dodge a problem we don't have is the textbook "two systems instead of one" smell.

### Option C — Drop SSE for v1; ship final-response-only

Defeats the §10.1 UX contract. The architecture doc lists this as the unacceptable fallback and we agree.

### Option D — Keep daphne; fix the Caddy buffering; add a per-view ASGI hygiene checklist  *(RECOMMENDED)*

What we actually need to do, in order:

1. **Add `flush_interval -1` to the `backend:8000` reverse_proxy block** in `deploy/Caddyfile`, scoped to the SSE endpoint with a sub-handler. Pattern: copy the Volt MCP block at lines 132–141 and target `/api/v1/leases/templates/*/ai-chat-v2/`. (See §3 step 2 for the exact diff.)
2. **Make the lease-AI v2 view `async def`** so the SSE generator runs as a native async iterator, not a sync iterable wrapped by daphne's threading shim. Convert ORM access via `sync_to_async` or `database_sync_to_async` (already in use across `apps.leases.consumers`).
3. **Wire the `X-Accel-Buffering: no` response header** on the SSE response. Some intermediaries (CDN, browser dev-tools proxy) honour this; cheap insurance.
4. **Set `keepalive: yes` (interval ~25s) in the SSE generator** to keep idle connections from being garbage-collected by intermediate proxies. Send a `: ping\n\n` comment line.
5. **Add a daphne worker-count check to the regression battery** — the lease-AI pipeline can hold a connection open for 20–30 s; under load, daphne's default 100 max connections per worker is fine for the v1 traffic but worth tracking. (Today: 1 daphne worker, room for hundreds of concurrent SSE sessions before back-pressure.)

**Cost:** ~half a day to ship + one staging-deploy test cycle. Zero code-architecture risk: we're not changing any framework choice.

---

## 3. Recommendation: Option D

**Lock Option D.** The existing daphne ASGI runtime already solves the problem the audit flagged; the proxy-buffering gap is a 1-line Caddy fix; the per-view discipline is a checklist, not a migration.

Concrete plan:

### Step 1 — Convert the v2 view to `async def` (in Phase 2)

The v2 endpoint lives in a new `LeaseTemplateAIChatV2View`. Pattern after `apps.leases.consumers` for async ORM access. Sync helpers (e.g. `agency.get_active_corpus()`) wrap with `sync_to_async`.

```python
# apps/leases/template_views_v2.py
from asgiref.sync import sync_to_async
from django.http import StreamingHttpResponse
from rest_framework.views import APIView

class LeaseTemplateAIChatV2View(APIView):
    permission_classes = [IsAuthenticated, AgencyMemberOrAdmin]

    async def post(self, request, template_id):
        # ... build LeaseContext via sync_to_async(Front Door logic)
        runner = LeaseAgentRunner(request_id=..., intent=...)

        async def sse_generator():
            yield "event: status\ndata: {...}\n\n"
            async for evt in run_pipeline(runner, ...):
                yield format_sse(evt)
            yield "event: done\ndata: ...\n\n"

        resp = StreamingHttpResponse(sse_generator(), content_type="text/event-stream")
        resp["X-Accel-Buffering"] = "no"
        resp["Cache-Control"] = "no-cache, no-transform"
        return resp
```

DRF's `APIView` supports `async def post` natively as of Django 4.1+ (we are on 5.2). Auth, throttling, and permissions all run as sync via `sync_to_async` inside `dispatch`; no work needed.

### Step 2 — Caddy diff (lift verbatim from the existing Volt MCP pattern at lines 132–141)

```caddy
# deploy/Caddyfile (production block, around line 145)

# SSE endpoint for lease-AI v2 — disable Caddy's buffering so events flush.
# Pattern matches the Volt MCP `flush_interval -1` block at lines 132–141.
handle /api/v1/leases/templates/*/ai-chat-v2/* {
  reverse_proxy backend:8000 {
    flush_interval -1
    transport http {
      read_timeout 180s
      write_timeout 180s
    }
  }
}

# Main Django API proxy — generous timeouts for AI endpoints
reverse_proxy backend:8000 {
  transport http {
    read_timeout 180s
    write_timeout 180s
  }
}
```

Same staging block needs the same handler.

### Step 3 — Add a smoke test in the regression battery

Hits `/ai-chat-v2/` against the local stack and asserts that the first `event: agent_started` byte arrives within 2 s of POST (proves the proxy is flushing). Failure mode today: a buffered Caddy will hold all bytes until the response closes; the smoke test would deadlock and fail.

### Step 4 — Sentry

`SentryAsgiMiddleware` is wired in `config/asgi.py` already (websocket path). Confirm the HTTP path picks up Sentry's ASGI integration; if not, add it.

---

## 4. Risks and mitigations

| # | Risk | Likelihood | Mitigation |
|---|---|---|---|
| R1 | A sync middleware (e.g. our agency-tenancy middleware) blocks the async view and we silently degrade to a sync-to-async wrap that serialises. | Medium — we have ~15 middleware in `config/settings/base.py`. | Add `async-tagged` markers in code review; daphne logs `sync handler in async context` warnings. Run an end-to-end load test before Phase 6 cutover. |
| R2 | DRF auth/permission classes (sync) blocking long-running SSE responses. | Low — they run pre-stream, not during. | Confirm with a probe: log the elapsed time between `dispatch` start and first SSE byte. Should be <200ms; if higher, something is mis-wrapping. |
| R3 | Sentry / observability not capturing SSE errors mid-stream. | Medium — long-lived response, easy for errors mid-generator to be swallowed. | Wrap the SSE generator body in a try/except that emits a final `event: error` SSE frame + `sentry_sdk.capture_exception(exc)` before yielding the terminal frame. |
| R4 | Caddy timeout (180s in our config) kills the connection before pipeline finishes. | Low — the LeaseAgentRunner caps wall-clock at 90s. | Pipeline cap (90s) < proxy cap (180s) by design. If the cap is ever raised, raise Caddy in lock-step. |
| R5 | Browser EventSource auto-reconnect causes duplicate runs on flaky networks. | Low — frontend uses `fetch + ReadableStream`, not `EventSource`, per §10.2. | Document this in the v2 frontend spec; idempotency key from `request_id` deduplicates server-side via `AILeaseAgentRun.request_id unique=True`. |

---

## 5. Cost

- **Engineering:** ~0.5 day to land the Caddy diff + smoke test + v2 view scaffold. Ride along with Phase 2 (Drafter + Reviewer) which already needs the view.
- **Deploy:** one staging deploy, one prod deploy. No DB migration. No service restart beyond Caddy reload (zero-downtime).
- **Rollback:** revert the Caddyfile commit; v2 endpoint stays available but SSE will buffer (same as v1 behaviour today). Not an outage; user just sees the spinner longer.

---

## 6. Decision deadline

**This ADR must be approved before Phase 1 kicks off** because the v2 view shape (`async def post`) is a Phase 2 deliverable that depends on the runtime call. If Option D is rejected and we instead split out a FastAPI sub-app, Phase 2 LOC roughly doubles (dual stack). The opportunity cost of indecision compounds quickly.

Target: MC sign-off within 24 h of this ADR landing.

---

## 7. Open follow-ups (not blocking)

- Run a load test of 50 concurrent SSE sessions against daphne on staging before the Phase 6 cutover. Daphne handles concurrency well in theory; we want a real number for the runbook.
- Document the SSE event-type vocabulary (already specified in §10.2 of the architecture doc) as an OpenAPI-style spec at `docs/system/lease-ai-sse-events.md` so the frontend has a stable contract.
- Investigate whether to keep daphne or migrate to uvicorn-workers + gunicorn for HTTP-only paths in Phase 7+. Daphne is fine today; uvicorn is faster for HTTP-only workloads. Not relevant to lease-AI v2.
