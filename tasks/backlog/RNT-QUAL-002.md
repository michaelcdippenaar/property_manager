---
id: RNT-QUAL-002
stream: rentals
title: "Lease generation: retry + graceful fallback when Gotenberg fails"
feature: ai_lease_generation
lifecycle_stage: 6
priority: P1
effort: S
v1_phase: "1.0"
status: backlog
asana_gid: "1214177452426023"
assigned_to: null
depends_on: []
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Today a Gotenberg outage breaks every lease/PDF flow with a 500. Add retries with backoff and a graceful user-facing message + async retry queue so an operator doesn't lose their work.

## Acceptance criteria
- [ ] Gotenberg client: 3 retries with exponential backoff (1s → 2s → 4s) for 5xx / timeout
- [ ] On final failure: lease render task enqueued to Celery for retry in 5 min (up to 3 retries)
- [ ] UI: if render fails synchronously, show "Preparing your document — we'll email you when ready" instead of red error
- [ ] Operator sees pending render jobs in admin with retry CTA
- [ ] Metrics: Gotenberg success rate counter + p95 latency exposed to Sentry/monitoring

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
