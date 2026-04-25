---
id: RNT-AI-005
stream: rnt-ai
title: "AI chat performs all user functions via MCP tool registry"
feature: ""
lifecycle_stage: null
priority: P2
effort: XL
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: [DEC-025, RNT-AI-002]
asana_gid: "1214278059927096"
created: 2026-04-25
updated: 2026-04-25
---

## Goal

Expand the AI chat action-execution layer so that every primary user function in the admin SPA is executable through the AI chat, backed by an internal MCP-style tool registry at `backend/apps/ai/tools/`.

## Acceptance criteria

- [ ] Architecture doc written at `docs/ai/mcp-tool-contract.md` covering: tool definition schema, role-bounded permissions, audit trail, confirmation gating, error surface, and idempotency keys.
- [ ] Backend tool registry at `backend/apps/ai/tools/` with one module per tool. Each tool exposes: name, description (LLM-readable), JSON schema for args, role check, execution via existing service layer (no direct ORM writes), structured result.
- [ ] AI guide endpoint accepts `tool_call` responses from the LLM and dispatches to the registry; tool results stream back to the chat.
- [ ] Confirmation gate: write operations show a confirmation card in the chat ("Create property '18 Doctor Malan Road' for owner X — Confirm?") before executing, unless the user has enabled "auto" mode.
- [ ] Audit log entry per tool execution: actor, tool name, args, result, timestamp.
- [ ] All 10 listed tools implemented with at least 1 happy-path pytest each:
  1. `create_entity` (owner / landlord — individual or company)
  2. `create_property` (address, optional photos, owner FK)
  3. `create_lease` (tenant, property, term, rent)
  4. `create_template` (lease template scaffold from prompt)
  5. `sign_lease` (initiate e-signing flow on an existing lease)
  6. `advertise_property` (publish to listing channels — channel list TBD)
  7. `create_tenant`
  8. `create_maintenance_request`
  9. `link_owner_to_property`
  10. `upload_document_to_entity`
- [ ] Frontend: chat renders tool-call cards inline with confirm/cancel buttons; successful execution shows a success card with a link to the created object (`admin/src/components/ai/ToolCallCard.vue`).
- [ ] Entire feature gated behind feature flag `AI_TOOLCALL_ENABLED` (default: `False`). Roll-out order starts with `create_property` (= RNT-AI-002 pattern).
- [ ] Telemetry events tracked: `tool_call_attempted`, `tool_call_succeeded`, `tool_call_failed`.

## Files likely touched

- `backend/apps/ai/tools/__init__.py` (new)
- `backend/apps/ai/tools/create_entity.py` (new)
- `backend/apps/ai/tools/create_property.py` (new)
- `backend/apps/ai/tools/create_lease.py` (new)
- `backend/apps/ai/tools/create_template.py` (new)
- `backend/apps/ai/tools/sign_lease.py` (new)
- `backend/apps/ai/tools/advertise_property.py` (new)
- `backend/apps/ai/tools/create_tenant.py` (new)
- `backend/apps/ai/tools/create_maintenance_request.py` (new)
- `backend/apps/ai/tools/link_owner_to_property.py` (new)
- `backend/apps/ai/tools/upload_document_to_entity.py` (new)
- `backend/apps/ai/views.py` (tool_call dispatch)
- `backend/apps/ai/prompts/` (system prompt updated with tool contract)
- `backend/apps/ai/tests/test_tools_*.py` (new test modules)
- `admin/src/components/ai/ToolCallCard.vue` (new)
- `admin/src/components/ai/AiChat.vue` (render tool-call messages)
- `admin/src/stores/aiGuide.ts`
- `docs/ai/mcp-tool-contract.md` (new)

## Test plan

**Manual:**
1. Enable `AI_TOOLCALL_ENABLED=True` in local env.
2. Open AI chat. Type: "Create a new property at 18 Doctor Malan Road for owner Jane Smith."
3. Verify: confirmation card appears in chat with correct details.
4. Click Confirm. Verify: success card appears with link to the new property.
5. Navigate to the property — confirm it was created correctly.
6. Repeat a representative selection of the other 9 tools.
7. Disable flag — confirm no tool-call UI appears and chat falls back to read-only mode.

**Automated:**
- `cd backend && pytest apps/ai/tests/test_tools_*.py` — happy-path and role-check tests for all 10 tools.
- Playwright E2E: chat → create_property tool flow → confirmation → success card → link navigates to property.

## Handoff notes

(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-25 — rentals-pm: Task created. This is a flagship multi-week capability. Blocked on DEC-025 (action-execution scope decision) and RNT-AI-002 (first tool pattern established). Do not begin implementation until both dependencies are resolved. Roll out tool-by-tool starting with create_property.
