---
discovered_by: rentals-implementer
discovered_during: RNT-QUAL-007
discovered_at: 2026-04-23
priority_hint: P2
suggested_prefix: RNT-QUAL
---

## What I found
The push notification deep-link screen→route mapping in `agent-app/src/services/push.ts` references route paths (`/leases/:id`, `/mandates/:id`, `/payments/invoices/:id`) that may not all exist in the current agent-app router. Similarly, the tenant service worker maps to `/maintenance/:id` and `/payments/:id` which need verification against the live router.

## Why it matters
If a user taps a push notification and the route doesn't exist, the app silently fails to navigate. Deep-links are a key UX feature — broken ones erode trust.

## Where I saw it
- `agent-app/src/services/push.ts` — `SCREEN_ROUTES` mapping (lines ~18-22)
- `tenant/public/sw.js` — `urlMap` in `notificationclick` handler
- `agent-app/src/router/index.ts` — needs audit against the screen map

## Suggested acceptance criteria (rough)
- [ ] Audit `agent-app/src/router/index.ts` against all `SCREEN_ROUTES` entries; add missing routes or update screen names
- [ ] Audit `tenant/src/router/index.ts` against all `urlMap` entries; add missing routes or update paths
- [ ] Manual smoke-test: tap each notification type on a real device, verify correct screen opens

## Why I didn't fix it in the current task
Requires reading all agent-app page components to map IDs to correct detail routes. In-scope but would require significant router work beyond the push dispatch scope.
