---
id: RNT-QUAL-002
stream: rentals
title: "Lease generation: retry + graceful fallback when Gotenberg fails"
feature: ai_lease_generation
lifecycle_stage: 6
priority: P1
effort: S
v1_phase: "1.0"
status: testing
asana_gid: "1214177452426023"
assigned_to: tester
depends_on: []
created: 2026-04-22
updated: 2026-04-23
---

## Goal
The Gotenberg client already has 3-retry exponential backoff (1s → 2s → 4s). What is missing: when all retries are exhausted the caller raises uncaught, hitting the user as a 500. Add a Celery async fallback, a graceful UI pending state, and admin visibility into pending render jobs.

## Acceptance criteria
- [x] ~~Gotenberg client: 3 retries with exponential backoff (1s → 2s → 4s) for 5xx / timeout~~ DONE — `apps/esigning/gotenberg.py` line 14, `MAX_RETRIES` logic lines 68–168
- [x] On final Gotenberg failure: lease render task enqueued for background retry in 5 min (up to 3 attempts) — `ExportTemplatePDFView` in `template_views.py` creates `PdfRenderJob` + calls `enqueue_pdf_render(job.id)`; worker in `tasks.py` retries via daemon thread (no Celery in this project — fire-and-forget threads are the established pattern per tasks.py docstring)
- [x] UI: if render fails synchronously, show "Preparing your document — we'll email you when ready" instead of red error — `TemplateEditorView.vue` handles 202 response and surfaces the message as an info toast; also navigates to `/leases/render-jobs` so operator can monitor the job
- [x] Operator sees pending render jobs in admin with retry CTA — `PdfRenderJobsView.vue` at `/leases/render-jobs` shows all jobs with status badges, attempt count, error text, download link for done jobs, and a Retry button for failed/pending jobs
- [x] Metrics: counter emitted on final failure path — `_increment_counter('gotenberg.pdf.failure', ...)` fires on every failed attempt including the last one (lines 140–143 and 157–162 in `gotenberg.py`)

## Files likely touched
- `backend/apps/leases/pdf_service.py` (or equivalent Gotenberg client)
- `backend/apps/leases/tasks.py` (Celery task)
- `admin/src/views/leases/LeaseDetail.vue` (pending state)

## Test plan
**Automated:**
- `pytest backend/apps/leases/tests/test_pdf_resilience.py` — 5xx triggers retry, final failure enqueues task, success emits event

**Manual:**
- Stop Gotenberg container → try to generate lease → UI shows "we'll email you" not a 500 → restart Gotenberg → Celery retry succeeds

## Handoff notes
2026-04-23: Dedup sweep — backoff AC already delivered in `apps/esigning/gotenberg.py`. Remaining scope: Celery async fallback on final failure, UI graceful degradation, and admin pending render queue. Task kept; scope narrowed above.

2026-04-23 (implementer): All four remaining acceptance criteria were already implemented in a prior pass — the code matched the ACs exactly. The only genuine gap was UX discoverability: when Gotenberg fails and a job is queued, the operator received the "we'll email you" toast but had no path to the render queue. Fixed by adding `router.push('/leases/render-jobs')` in both the `.then()` 202 branch and the `.catch()` 202 branch of `exportPDF()` in `TemplateEditorView.vue`. All 13 automated tests in `test_pdf_resilience.py` pass. No other files changed. Note: the task mentions "Celery" but this project uses fire-and-forget daemon threads (documented at the top of `tasks.py`); the retry behaviour is functionally identical — reviewer should confirm this is acceptable or file a discovery if true Celery is required.

2026-04-23 (reviewer): Review passed. Verified: (1) 3-retry exponential backoff at `apps/esigning/gotenberg.py:69,130,166-168`; (2) `PdfRenderJob` model + `enqueue_pdf_render` worker thread + 202 response at `template_views.py:1897-1914`; (3) UI 202 handling + router.push to `/leases/render-jobs` in `TemplateEditorView.vue` both branches; (4) operator view `PdfRenderJobsView.vue` with retry CTA; (5) `gotenberg.pdf.failure` counter at `gotenberg.py:141,158`. Security: `PdfRenderJobListView`/`RetryView` both use `IsAgentOrAdmin` with role-scoped querysets (admin all, agent own) — no IDOR; no PII in logs. `pytest test_pdf_resilience.py` → 13 passed. Re: daemon-thread vs Celery — this project's established pattern per `tasks.py` docstring; acceptable.
