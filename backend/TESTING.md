# Tremly Backend — Testing Guide

## Quick start

```bash
cd backend
pytest apps/properties/tests/test_dashboard_cache.py -xvs   # single module
pytest apps/test_hub/ -q                                      # full suite
pytest apps/test_hub/ -q --create-db                         # force DB recreation
```

## Test database lifecycle (`--reuse-db`)

`pytest.ini` sets `--reuse-db` in `addopts`.  This means:

- **First run (no DB yet):** pytest-django creates `test_klikk_db` and runs all
  migrations.  The DB is kept after the session ends.
- **Subsequent runs:** the existing DB is reused.  No migration time overhead.
- **Schema changed:** run `pytest --create-db` once to rebuild the DB.

### Why `--reuse-db`?

Without `--reuse-db`, a leftover `test_klikk_db` from a crashed previous run
causes pytest-django to destroy-then-recreate the DB at the START of the next
session.  If two `django.test.TestCase` subclasses live in the same module,
Django's `TestCase.tearDownClass()` closes all connections after the first
class finishes.  When the DB is simultaneously being recreated (destroy +
migrate), the second class finds a missing DB during its `setUpClass()`
atomic-block entry.

`--reuse-db` prevents this by never destroying the DB between runs.  Use
`--create-db` explicitly whenever you need a clean slate (e.g. after adding
new migrations).

## Base test class: `TremlyAPITestCase`

All integration tests inherit from
`apps.test_hub.base.test_case.TremlyAPITestCase`.

### `_JsonAPIClient` — always-JSON client

`TremlyAPITestCase` sets `client_class = _JsonAPIClient`.  This subclass
overrides `request()` to inject `Accept: application/json` as a default on
every request, preventing DRF's browsable HTML renderer from firing in tests.
You can always call `resp.json()` without passing `HTTP_ACCEPT` on each call.

### Factory helpers

| Method | Creates |
|--------|---------|
| `create_user(email, role)` | `User` |
| `create_admin/agent/tenant/owner_user()` | role-specific `User` |
| `create_person(full_name, linked_user)` | `Person` |
| `create_property(agent, name)` | `Property` |
| `create_unit(property_obj)` | `Unit` |
| `create_lease(unit, primary_tenant)` | `Lease` |
| `create_maintenance_request(unit)` | `MaintenanceRequest` |
| `authenticate(user)` | calls `force_authenticate` on `self.client` |
| `get_tokens(user)` | returns `{access, refresh}` JWT strings |

## Multi-class test modules

When a single `.py` file contains two or more `TestCase` subclasses, both DB
and client settings apply correctly because:

1. `django_db_setup` is `session`-scoped in pytest-django — one DB per run.
2. `_JsonAPIClient` is set at class level, so every test instance gets it
   regardless of whether the test's `setUp` calls `super().setUp()`.
3. `--reuse-db` prevents the stale-DB teardown race described above.

Do **not** set `class_atomics` or `@pytest.mark.django_db(transaction=True)`
unless your test genuinely needs a `TransactionTestCase` — it will bypass the
transaction rollback and leave data in the DB for subsequent tests.

## TDD markers

| Marker | Meaning |
|--------|---------|
| `@pytest.mark.red` | xfail(strict=True) — implementation not written yet |
| `@pytest.mark.green` | must pass |
| `@pytest.mark.unit` | no DB, fast |
| `@pytest.mark.integration` | uses DB + API client |
| `@pytest.mark.e2e` | hits external services (Gotenberg, Firebase) |
| `@pytest.mark.slow` | known slow test |
| `@pytest.mark.flaky` | quarantined pending investigation |
