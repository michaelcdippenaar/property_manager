---
discovered_by: rentals-implementer
discovered_during: RNT-002
discovered_at: 2026-04-23
priority_hint: P1
suggested_prefix: RNT-SEC
---

## What I found
`LeaseBuilderSessionCreateView.post()` accepts `existing_lease_id` in the request body to pre-populate a session from an existing lease. There is no ownership/access check — any authenticated agent can pass any lease ID and read its data (tenant name, rent, property address) into their own builder session.

## Why it matters
IDOR: an agent working for Agency A can read sensitive lease data belonging to Agency B tenants by guessing or brute-forcing lease IDs. This exposes PII (tenant names, contact details, property addresses, rent amounts) covered by POPIA. The existing integration test `test_idor_create_session_any_lease` in `apps/test_hub/leases/integration/test_builder.py` documents this issue.

## Where I saw it
- `backend/apps/leases/builder_views.py:244-252` — `Lease.objects.select_related(...).get(pk=existing_lease_id)` with no user/property scope filter
- `backend/apps/test_hub/leases/integration/test_builder.py:65-84` — test explicitly documents the vulnerability

## Suggested acceptance criteria (rough)
- [ ] `existing_lease_id` lookup is scoped to leases accessible to the requesting user (via `get_accessible_property_ids` or equivalent)
- [ ] Return 404 (not 403) when the lease is not accessible — prevents ID enumeration
- [ ] Test: another agent's lease ID returns 404

## Why I didn't fix it in the current task
Access scoping depends on the role/property-assignment model used elsewhere in `views.py` (`get_accessible_property_ids`). Adding the filter here is a 3-5 line change but touches security policy — should be reviewed as a dedicated security task to ensure consistent RBAC enforcement.
