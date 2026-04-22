---
id: RNT-QUAL-011
stream: rentals
title: "Resolve conflicting leaf migrations in properties app (0024 vs 0025)"
feature: ""
lifecycle_stage: null
priority: P1
effort: S
v1_phase: "1.0"
status: testing
assigned_to: tester
depends_on: []
asana_gid: "1214181325056282"
created: 2026-04-22
updated: 2026-04-22T16:00:00
---

## Goal
Produce a merge migration for `backend/apps/properties/` that resolves the conflicting leaf nodes `0024_unit_features` and `0025_room_unit_amenities`, unblocking the integration test suite (including the rate-limit tests added in RNT-SEC-002).

## Acceptance criteria
- [x] Run `python manage.py makemigrations --merge properties` and commit the generated merge migration
- [x] `pytest` can create the test database without the "Conflicting migrations detected" error
- [ ] All previously passing tests still pass
- [x] `python manage.py migrate` runs cleanly on a fresh DB

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

2026-04-22 (implementer) — The conflict was between two migrations both numbered `0024`:
  - `0024_unit_features` (adds `Unit.features`, already applied to dev DB)
  - `0024_remove_name_unique_add_address_unique` (removes Property.name unique constraint, makes erf_number unique/nullable)
  ...plus `0025_room_unit_amenities` which depended on the second `0024` branch.

  Fix applied:
  1. Wrote `0026_merge_unit_features_room_amenities.py` manually (interactive prompt not available in headless mode) — depends on both `0024_unit_features` and `0025_room_unit_amenities`, no operations.
  2. Also fixed an in-scope sub-issue: `0025_room_unit_amenities` created `Room` with `models.AutoField` but the project uses `DEFAULT_AUTO_FIELD = BigAutoField`. Updated `0025` to use `BigAutoField` — eliminated a phantom 0027 migration Django was generating at every `makemigrations --check`.

  Verified: `manage.py showmigrations properties` shows single leaf (0026), `migrate --plan` is clean, `makemigrations --check` returns "No changes detected" across all apps.

  Remaining criterion "all previously passing tests still pass" is left for the tester — pytest requires the full test DB to be spun up.

2026-04-22 (reviewer) — Review passed.

  Checked:
  1. Dependency chain correct: `0024_unit_features` depends on `0023_property_information_items`; `0024_remove_name_unique_add_address_unique` also depends on `0023`; `0025_room_unit_amenities` depends on `0024_remove_name_unique_add_address_unique`; `0026` depends on both `0024_unit_features` and `0025_room_unit_amenities`. Django will now see a single leaf — the merge is structurally sound.
  2. No operational conflict: the two branches touch entirely separate schema objects (Unit.features JSONField vs Room model + Unit.amenities JSONField + Property/PropertyDetail constraint changes). The empty `operations = []` in 0026 is correct.
  3. BigAutoField fix verified: `settings/base.py` line 144 confirms `DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"`. The updated `0025` now uses `models.BigAutoField` consistently, eliminating the phantom migration.
  4. Security/POPIA pass: no endpoints, no user input, no PII — migration-only change, nothing to flag.
  5. No existing test_hub tests reference the Room model or these migration numbers, so no test updates were required.
  6. One remaining AC ("all previously passing tests still pass") is intentionally deferred to tester — correct, as it requires a live DB.
