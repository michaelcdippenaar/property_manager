---
discovered_by: rentals-reviewer
discovered_during: RNT-SEC-035
discovered_at: 2026-04-23
priority_hint: P1
suggested_prefix: RNT-SEC
---

## What I found
`MaintenanceRequestViewSet` declares `_WRITE_ACTIONS = {"create", "update", "partial_update", "destroy"}` but `get_permissions()` only branches on `destroy`. The `create`, `update`, and `partial_update` actions are still guarded only by `IsAuthenticated`, meaning owners (and tenants) can POST new maintenance requests and PATCH existing ones through the API unchallenged.

## Why it matters
Owners should be read-only on the agent-facing maintenance API. The misleading `_WRITE_ACTIONS` constant gives reviewers and developers a false impression that all write actions are protected, masking the real gap.

## Where I saw it
- `backend/apps/maintenance/views.py:46` — `_WRITE_ACTIONS` set declared but never used in `get_permissions()`
- `backend/apps/maintenance/views.py:48-58` — `get_permissions()` only branches on `_AGENT_ONLY_ACTIONS` and `destroy`

## Suggested acceptance criteria (rough)
- [ ] `MaintenanceRequestViewSet.get_permissions()` returns `[IsAgentOrAdmin()]` for `create`, `update`, and `partial_update` actions (or use `_WRITE_ACTIONS` set properly)
- [ ] Tests added to `TestOwnerReadOnly` asserting 403 on owner POST and PATCH to `/api/v1/maintenance/`
- [ ] Existing tenant create-flow tests (tenant raises a request) remain unaffected — tenant should still be able to create, so the guard may need role-specific logic rather than a blanket IsAgentOrAdmin

## Why I didn't fix it in the current task
RNT-SEC-035 acceptance criteria only required blocking `destroy` for owners. Expanding to create/update/partial_update is a separate decision (especially because tenant create is a legitimate flow) and would double the scope of this diff.
