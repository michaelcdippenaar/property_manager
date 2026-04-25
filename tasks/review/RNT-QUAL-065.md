---
id: RNT-QUAL-065
stream: rentals-quality
title: "Remove debug console.log statements from lease template editor and dashboard shell"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214273917256991"
created: 2026-04-24
updated: 2026-04-24
---

## Goal

Delete all six debug `console.log` calls (with `[LOAD]`, `[SAVE]`, `[STORE SAVE]`, `[dashboard]` prefixes) from the lease template editor and agency shell before v1 launch.

## Acceptance criteria

- [ ] `admin/src/views/leases/TemplateEditorView.vue` lines 1513-1514 and 1910-1911: `console.log` calls removed.
- [ ] `admin/src/stores/template.ts` lines 125 and 131: `console.log` calls removed.
- [ ] `admin/src/views/dashboard/AgencyShellView.vue` line 50: `console.log` call removed.
- [ ] Any `eslint-disable-next-line no-console` comments accompanying the removed lines are also deleted.
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
