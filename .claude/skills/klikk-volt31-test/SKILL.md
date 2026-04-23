---
name: klikk-volt31-test
description: >
  Vault33 / The Volt test battery — runs the full integration test suite
  covering unique-field validation, relationship catalogue enforcement,
  PATCH semantics, soft-delete behaviour, and the family-relationship seed.
  Use whenever the user wants to verify Vault33 regressions, test the
  entity validator, check relationship types, or validate the gateway
  smoke/mcp/internal flows. Triggers on mentions of "vault33 test",
  "volt test", "entity validator", "relationship test", "vault smoke",
  or asks to run the Vault33 test battery.
---

# Vault33 / The Volt — Test Battery

End-to-end + unit coverage for Vault33's owner-facing entity validator,
relationship catalogue, and the three gateway flows (subscriber, internal,
MCP manifest-then-fetch).

The battery is split into four live-server scripts + one Django unit
test module. All live scripts self-bootstrap Django (`vault33.settings.dev`)
and target `http://localhost:8001` by default (override with
`VAULT33_BASE_URL`).

---

## When to use this skill

- "Run the Vault33 test battery"
- "Test the entity validator" / "check unique_id / tax_number validation"
- "Verify the family relationship seed"
- "Run the gateway smoke" / "MCP smoke" / "internal vault bridge smoke"
- "Did anything regress on Vault33?"
- Before merging any change to `apps/entities/serializers.py`,
  `apps/entities/models.py`, `apps/gateway/`, or `apps/the_volt/migrations/`

---

## Scripts available

All under `backend/scripts/` in `/Users/mcdippenaar/PycharmProjects/vault33/`.

| Script | What it covers |
|---|---|
| `gateway_smoke.py` | Full subscriber gateway: request → OTP recovery → public approve → REST checkout with inline package + HMAC signature. |
| `mcp_delivery_smoke.py` | MCP manifest-then-fetch: checkout returns pointer manifest, subscriber follows `mcp_endpoint`, second `DataCheckout` row created as fetch audit, append-only enforcement, foreign-subscriber 404. |
| `internal_gateway_smoke.py` | Service-to-service internal vault bridge (`X-Volt-Internal-Token`). |
| `volt31_test_battery.py` | Unique-field validator + relationship catalogue + family seed + PATCH self-exclusion + soft-delete release. |

Each script uses the same `ok()` / `fail()` pattern: green check on pass,
red banner + `sys.exit(1)` on first failure. Tag-based cleanup runs in
`finally` so repeated runs stay idempotent.

---

## Unit test module

`backend/apps/entities/tests/test_unique_fields.py` — Django `TestCase` style.

```bash
cd /Users/mcdippenaar/PycharmProjects/vault33/backend
.venv/bin/python manage.py test apps.entities.tests.test_unique_fields -v 2 --noinput
```

Classes:

| Class | Coverage |
|---|---|
| `TestUniqueIdNumber` | Blocks personal dup, allows company with same id_number (different group), releases claim on soft-delete. |
| `TestUniqueTaxNumber` | Blocks personal↔company (crosses entity types). |
| `TestUniqueRegNumber` | Blocks company↔company, company↔CC; allows trust carrying reg_number. |
| `TestPatchSelf` | PATCH same entity with its own id_number → 200. |
| `TestFamilyRelationships` | All 4 family codes seeded; corporate `parent_of` rejects personal→personal. |

Runs under 15 s against a fresh test database.

---

## Prerequisites

1. Backend running on `http://localhost:8001`:
   ```bash
   cd /Users/mcdippenaar/PycharmProjects/vault33/backend
   .venv/bin/python manage.py runserver 0.0.0.0:8001 > /tmp/vault33-backend.log 2>&1 &
   ```
2. Owner user seeded: `admin@vault33.local` / `admin`
   (created by `scripts/seed_fixtures.py`).
3. Venv at `backend/.venv/` with requirements installed.
4. Settings module `vault33.settings.dev` (live log to `/tmp/vault33-backend.log`
   — the MCP/gateway smokes tail it to recover dev-mode OTPs).

---

## Running everything

Single shell block — stops on first failure thanks to `&&`:

```bash
cd /Users/mcdippenaar/PycharmProjects/vault33/backend && \
  .venv/bin/python manage.py test apps.entities.tests.test_unique_fields -v 2 --noinput && \
  .venv/bin/python scripts/volt31_test_battery.py && \
  .venv/bin/python scripts/gateway_smoke.py && \
  .venv/bin/python scripts/mcp_delivery_smoke.py && \
  .venv/bin/python scripts/internal_gateway_smoke.py && \
  echo "=== FULL VAULT33 BATTERY PASSED ==="
```

Expected total runtime: ~25–40 seconds.

---

## Interpreting output

- **Green `✓`** next to each assertion line = step passed.
- **Green banner** `=== ... PASSED ===` at the end = entire script passed.
- **Red banner** `FAILED: <msg>` + `sys.exit(1)` = first failing assertion.
  Everything before the red banner already ran — read upward from the banner
  to find the last green check, the failure is in the next step.

Where to look when something goes wrong:

| Symptom | Check |
|---|---|
| `cannot reach http://localhost:8001/health/` | Backend not running, or bound to a different port. |
| OTP not recovered | `/tmp/vault33-backend.log` missing `VOLT_OTP_DEV_MODE` lines — verify `VOLT_OTP_DEV_MODE=True` in `vault33.settings.dev`. |
| `owner user not found` | Run `scripts/seed_fixtures.py` to create `admin@vault33.local`. |
| Relationship-type lookup fails | Apply migrations: `manage.py migrate the_volt`. Family seed lives in migration `0011_seed_family_relationships`. |
| Unique-field test fails on live server | Stale test entities from a previous run — volt31 tags each row with `test_run_id` and cleans up in `finally`; if the process was killed mid-run, manually delete: `VaultEntity.objects.filter(data__has_key='test_run_id').delete()`. |

---

## Extending the battery

Add a new check to `volt31_test_battery.py` — the pattern is one numbered
section per check, using the shared `ok()` / `fail()` helpers:

```python
# --- Section N: description ---
r = requests.post(f"{BASE_URL}/api/v1/entities/", headers=headers, json={...}, timeout=10)
if r.status_code != 201:
    fail(f"step N expected 201, got {r.status_code}: {r.text[:400]}")
ok(f"step N succeeded (id={r.json()['id']})")
```

Two rules for new checks:

1. **Tag every entity you create** with `data["test_run_id"] = run_id` so the
   `finally` cleanup removes it. Otherwise repeated runs accumulate cruft.
2. **Use the live server** (REST) for behaviour being validated; drop to the
   ORM only for soft-delete state assertions and cleanup.

For a new unit test, add a `TestCase` to `test_unique_fields.py` and follow
the `_make_user()` / `_client()` helpers — they wire up a `VaultOwner` and
JWT-authenticated `APIClient` in two lines.

---

## Key files

| File | Purpose |
|---|---|
| `backend/apps/entities/serializers.py` | `VaultEntitySerializer.UNIQUE_DATA_FIELDS` + `.validate()`; `EntityRelationshipSerializer.validate()` |
| `backend/apps/entities/models.py` | `VaultEntity`, `EntityRelationship`, `RelationshipTypeCatalogue` |
| `backend/apps/the_volt/migrations/0011_seed_family_relationships.py` | Family relationship seed |
| `backend/apps/entities/tests/test_unique_fields.py` | Unit tests |
| `backend/scripts/volt31_test_battery.py` | E2E unique-fields + relationships battery |
| `backend/scripts/mcp_delivery_smoke.py` | MCP manifest/fetch smoke (model for new scripts) |
| `backend/scripts/gateway_smoke.py` | Full subscriber gateway smoke |
| `backend/scripts/internal_gateway_smoke.py` | Internal bridge smoke |
| `/tmp/vault33-backend.log` | Live server log, tailed by OTP-dependent smokes |
