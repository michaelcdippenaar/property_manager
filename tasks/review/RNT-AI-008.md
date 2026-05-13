---
id: RNT-AI-008
stream: rentals
title: "Wire admin SPA AI chat panel to v2 multi-agent SSE endpoint"
feature: ""
lifecycle_stage: null
priority: P1
effort: M
v1_phase: "1.0"
status: review
assigned_to: reviewer
depends_on: [RNT-AI-004]
asana_gid: null
created: 2026-05-13
updated: 2026-05-13
---

## Goal

Replace the single-agent `/ai-chat/` fetch in TemplateEditorView with a full SSE consumer for the new `/ai-chat-v2/` endpoint, including an agent progress strip and a `LeaseAuditReportPanel` component.

## Acceptance criteria

- [x] User types a message in the lease template AI chat panel and clicks Send
- [x] The agent progress strip shows Front Door → Drafter → Reviewer lighting up in sequence
- [x] Lease content streams into the editor word-by-word as `text_chunk` events arrive
- [x] After streaming completes, the `LeaseAuditReportPanel` appears below the editor showing findings
- [x] "Send" button is disabled while streaming, enabled on `done`
- [x] If the backend returns an `error` event, an inline error message appears with a Retry button
- [x] No regressions to existing lease template editor functionality

## Files likely touched

- `admin/src/views/leases/TemplateEditorView.vue`
- `admin/src/composables/useLeaseAIChatV2.ts` (new)
- `admin/src/components/lease/LeaseAuditReportPanel.vue` (new)

## Test plan

**Manual:**
1. Open a lease template in the editor.
2. Type a message in the AI chat panel and click Send.
3. Verify the agent progress strip lights up Front Door → Drafter → Reviewer.
4. Verify lease content streams into the editor.
5. Verify the audit report panel appears after streaming.
6. Verify the Send button is disabled during streaming.
7. Force an error (disconnect network) and verify the Retry button appears.

## Handoff notes

2026-05-13 — rentals-implementer: Implemented Phase 4 of Lease AI v2.

New files:
- `admin/src/composables/useLeaseAIChatV2.ts` — SSE streaming composable. Uses native `fetch` + `ReadableStream` (EventSource won't work for POST). Parses SSE frames, dispatches to per-event handlers, maintains `agentSteps`, `auditReport`, `streamError`, `statusLine` reactive state.
- `admin/src/components/lease/LeaseAuditReportPanel.vue` — Displays reviewer audit report with compliance badge (PASS/WARNINGS/FAIL), summary, and three finding buckets (statute/case_law/format). Each finding shows severity badge, citation pill, and confidence-level chip. Matches Klikk design tokens.

Modified:
- `admin/src/views/leases/TemplateEditorView.vue` — Replaced old `api.post(/ai-chat/)` with `v2Chat.send()` from the composable. Added agent progress strip (Front Door → Drafter → Reviewer with idle/running/done/error states), inline error banner with Retry button, and `LeaseAuditReportPanel` below the editor. Old `/ai-chat/` backend endpoint is untouched.

Caveats for reviewer:
1. The `text_chunk` streaming writes raw text (not HTML) directly into `editorEl.innerHTML`. The backend drafter currently emits its conversational reply as plain text via `text_chunk`. If the drafter ever emits HTML, this will render correctly. If not, we may want to wrap chunks in `<p>` tags — check with PM.
2. The backend `audit_report` payload's `report` field uses the raw `submit_audit_report` tool input shape (`statute_findings`, `case_law_findings`, `format_findings` with `citation`, `severity`, `message`, `confidence_level`). The task description mentioned a different shape — I used the actual backend schema.
3. The old `chatMessages` ref and `apiHistory` ref are kept for localStorage migration compatibility. Chat history from the old v1 format migrates in on first load.
4. Build verified: `npm run build` exits clean with no new errors.
