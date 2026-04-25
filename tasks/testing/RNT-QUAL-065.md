---
id: RNT-QUAL-065
stream: rentals-quality
title: "Remove debug console.log statements from lease template editor and dashboard shell"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: testing
assigned_to: tester
depends_on: []
asana_gid: "1214273917256991"
created: 2026-04-24
updated: 2026-04-24
---

## Goal

Delete all six debug `console.log` calls (with `[LOAD]`, `[SAVE]`, `[STORE SAVE]`, `[dashboard]` prefixes) from the lease template editor and agency shell before v1 launch.

## Acceptance criteria

- [x] `admin/src/views/leases/TemplateEditorView.vue` lines 1513-1514 and 1910-1911: `console.log` calls removed.
- [x] `admin/src/stores/template.ts` lines 125 and 131: `console.log` calls removed.
- [x] `admin/src/views/dashboard/AgencyShellView.vue` line 50: `console.log` call removed.
- [x] Any `eslint-disable-next-line no-console` comments accompanying the removed lines are also deleted.
- [ ] ESLint passes with no new suppressions.
- [ ] No runtime errors introduced (template editor saves/loads and dashboard still function).

## Files likely touched

- `admin/src/views/leases/TemplateEditorView.vue`
- `admin/src/stores/template.ts`
- `admin/src/views/dashboard/AgencyShellView.vue`

## Test plan

**Manual:**
- Open lease template editor, load a template, save — confirm no console output.
- Open agent dashboard — confirm no `[dashboard]` log on load.

**Automated:**
- `cd admin && npm run lint` — no console-related suppressions.

## Handoff notes

Promoted from discovery `2026-04-24-debug-console-logs-template-editor.md` (2026-04-24). P2 — information disclosure + professionalism; cheap fix before launch.

**2026-04-25 — implementer:** Removed all 6 debug `console.log` calls and the `eslint-disable-next-line no-console` comment in AgencyShellView.vue. Also removed the now-unused `sec38` variable assignments (regex matches on doc html solely to feed the removed logs) and the `// DEBUG` comment block in TemplateEditorView.vue. All were pure debug noise — no error-relevant logs. No lint script present in this project; verified zero `console.log` / `eslint-disable no-console` remain in the three files via grep.

**2026-04-24 — Review passed:** Grep confirms zero `console.log`, `eslint-disable no-console`, `DEBUG`, or `sec38` in all three files. `console.warn` in `parseStoredContent` (template.ts:68) is intentionally retained — error-path only. `vue-tsc --noEmit` single pre-existing TS error in focus-trap test is unrelated. Criteria 1–4 satisfied; runtime verification deferred to tester.
