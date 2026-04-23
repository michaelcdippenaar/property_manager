---
discovered_by: gtm-marketer
discovered_during: GTM-015
discovered_at: 2026-04-23
priority_hint: P1
suggested_prefix: OPS
---

## What I found
GTM-015 is a Plausible observability/engineering task (Vue SPA plugin wiring, Django server-side Events API, consent banner UI) that was assigned a GTM- prefix because it was discovered during GTM-006. The implementation work is entirely outside the GTM marketer's scope.

## Why it matters
If the task stays assigned to the GTM marketer it will never be implemented. Direct-app signups (the likely majority of campaign-link conversions) continue to drop Plausible events silently, understating funnel metrics and making it impossible to measure v1 launch campaign ROI accurately.

## Where I saw it
- `tasks/backlog/GTM-015.md` — acceptance criteria reference `admin/src/plugins/plausible.ts`, `admin/index.html`, and `backend/apps/accounts/views.py`
- `tasks/discoveries/2026-04-22-admin-spa-plausible-direct-traffic-gap.md` — original discovery note

## Suggested acceptance criteria (rough)
- [ ] Task re-prefixed as `OPS-NNN` and assigned to `klikk-ops-observability` or `rentals-implementer`
- [ ] If consent UX approach (in-app banner vs. server-side Events API) is undecided, a `DEC-` task is created first and GTM-015 depends on it
- [ ] Original GTM-015 acceptance criteria remain intact after re-assignment

## Why I didn't fix it in the current task
Out of scope. The GTM marketer has no skills or authority over Vue SPA code, Django backend views, or Plausible script injection. Fixing it would require the `klikk-ops-observability` or `klikk-rentals-implementer` agent.
