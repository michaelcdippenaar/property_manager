---
discovered_by: rentals-implementer
discovered_during: QA-009
discovered_at: 2026-04-23
priority_hint: P2
suggested_prefix: RNT-SEC
---

## What I found

`TenantConversationsListCreateView` (and other tenant portal views) use `permission_classes = [IsAuthenticated]` with no role restriction. Any authenticated user — including suppliers, agents, and owners — can create and read tenant AI chat sessions. Data is scoped by `user=request.user` so there is no cross-user leak, but suppliers/agents creating "tenant" conversations is semantically wrong.

## Why it matters

Low severity for data leakage (scoped by user) but creates junk data under non-tenant accounts. More importantly, the AI chat context builder (`build_tenant_context`) queries for the user's active lease and unit — for a supplier user with no lease this may raise unhandled exceptions or log confusing errors in production.

## Where I saw it

- `backend/apps/tenant_portal/views.py:TenantConversationsListCreateView` — `permission_classes = [IsAuthenticated]`
- Confirmed by `TestTenantPortalRBAC::test_supplier_conversation_is_scoped_to_supplier` in `tests/integration/test_rbac_matrix.py`

## Suggested acceptance criteria (rough)

- [ ] Add `IsTenant | IsAgentOrAdmin` permission to tenant portal conversation views, OR
- [ ] Keep IsAuthenticated but validate that the user has an active lease before allowing POST (returns 403 with "No active lease" for non-tenants)

## Why I didn't fix it in the current task

Out of scope for QA-009. Low risk since data is scoped by user, but worth capturing for the hardening pass.
