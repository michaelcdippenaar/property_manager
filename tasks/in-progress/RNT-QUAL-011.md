---
id: RNT-QUAL-011
stream: rentals
title: "Resolve conflicting leaf migrations in properties app (0024 vs 0025)"
feature: ""
lifecycle_stage: null
priority: P1
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214181325056282"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Produce a merge migration for `backend/apps/properties/` that resolves the conflicting leaf nodes `0024_unit_features` and `0025_room_unit_amenities`, unblocking the integration test suite (including the rate-limit tests added in RNT-SEC-002).

## Acceptance criteria
- [ ] Run `python manage.py makemigrations --merge properties` and commit the generated merge migration
- [ ] `pytest` can create the test database without the "Conflicting migrations detected" error
- [ ] All previously passing tests still pass
- [ ] `python manage.py migrate` runs cleanly on a fresh DB

## Files likely touched
- `backend/apps/properties/migrations/` (new merge migration file)

## Test plan
**Manual:**
- `cd backend && python manage.py migrate --run-syncdb` on a fresh DB — no errors

**Automated:**
- `cd backend && pytest` — all db-dependent tests must pass without the migration conflict error

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-22 — Promoted from discovery `2026-04-22-properties-migration-conflict.md` found during RNT-SEC-002. Blocks the full integration test suite. Fix is a single `makemigrations --merge` command but needs its own review pass.
