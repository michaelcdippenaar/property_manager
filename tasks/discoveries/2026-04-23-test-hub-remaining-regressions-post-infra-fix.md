---
discovered_by: rentals-implementer
discovered_during: RNT-QUAL-045
discovered_at: 2026-04-23
priority_hint: P2
suggested_prefix: RNT-QUAL
---

## What I found

After fixing the DB infrastructure failures in RNT-QUAL-045, 9 real regression failures remain in `pytest apps/test_hub/`. Three groups: (1) push token platform validation accepts any string (200 instead of 400), (2) health monitor endpoint returns 403 to admin users instead of expected data, (3) lease builder tests expect `AttributeError` which is no longer raised.

## Why it matters

These are green-marked tests that represent real regressions against the Rentals v1 feature set. They were previously hidden under the 347 infra failures and are now surfaced cleanly. Leaving them fails the "0 real regressions" bar for launch readiness.

## Where I saw it

- `apps/test_hub/accounts/integration/test_auth.py::PushTokenTests::test_register_push_token_invalid_platform` — POST with `platform="INVALID"` returns 200 instead of 400
- `apps/test_hub/maintenance/integration/test_monitor.py::AgentHealthCheckTests` (3 tests) — endpoint returns 403 to admin user; `resp.data` has no `overall` or `checks` keys
- `apps/test_hub/leases/integration/test_builder.py::LeaseBuilderSessionCreateTests::test_create_session_with_existing_lease` and `test_idor_create_session_any_lease` — `AttributeError` not raised on duplicate/IDOR session create
- `apps/test_hub/integrations/unit/test_vault33.py` (3 tests) — `ModuleNotFoundError: No module named 'vault33_client'` — vault33 is a separate product, these tests likely need to be skipped or the module installed

## Suggested acceptance criteria (rough)

- [ ] Push token endpoint validates `platform` field and returns 400 for unknown values
- [ ] Health monitor endpoint (`/api/v1/maintenance/monitor/health/`) accessible to admin users and returns `overall` + `checks` keys
- [ ] Lease builder create-session correctly raises/returns 400 on duplicate or IDOR session attempt
- [ ] Vault33 tests either skip cleanly when `vault33_client` is absent or the package is installed in dev dependencies

## Why I didn't fix it in the current task

Out of scope for RNT-QUAL-045 which was strictly about DB infrastructure failures. These are separate functional regressions each requiring their own investigation.
