---
id: RNT-QUAL-042
stream: rentals
title: "Tenant portal conversation views not restricted to tenant role"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214227864198350"
created: 2026-04-23
updated: 2026-04-23
---

## Goal

Restrict `TenantConversationsListCreateView` (and sibling tenant portal views) so that non-tenant authenticated users cannot create or list tenant AI chat sessions.

## Acceptance criteria
- [ ] `TenantConversationsListCreateView.permission_classes` enforces `IsTenant | IsAgentOrAdmin` (agent access for support tooling is acceptable), OR `POST` validates the requesting user has an active lease and returns 403 with `{"detail": "No active lease"}` if not
- [ ] Supplier `POST /api/v1/tenant-portal/conversations/` returns 403
- [ ] Owner `POST /api/v1/tenant-portal/conversations/` returns 403
- [ ] Tenant with active lease can still create and list conversations (no regression)
- [ ] `build_tenant_context` is not called for non-tenant users (eliminates unhandled exception risk on missing lease)
- [ ] `TestTenantPortalRBAC::test_supplier_conversation_is_scoped_to_supplier` updated to assert 403

## Files likely touched
- `backend/apps/tenant_portal/views.py` — `TenantConversationsListCreateView.permission_classes`
- `backend/apps/tenant_portal/permissions.py` (or shared permissions) — `IsTenant` permission class if not already present
- `backend/tests/integration/test_rbac_matrix.py` — `TestTenantPortalRBAC` assertions

## Test plan
**Manual:**
- Log in as a supplier; attempt `POST /api/v1/tenant-portal/conversations/` — expect 403
- Log in as a tenant with active lease; create a conversation — expect 201

**Automated:**
- `cd backend && pytest tests/integration/test_rbac_matrix.py -k "tenant_portal" -v`

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-23 rentals-pm: Promoted from discovery `2026-04-23-tenant-portal-not-restricted-to-tenants.md`. Discovered during QA-009. Low data-leakage risk (scoped by user) but junk-data and potential unhandled exception in `build_tenant_context` for non-tenant users make this worth fixing before launch.
