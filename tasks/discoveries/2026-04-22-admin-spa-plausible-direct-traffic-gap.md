---
discovered_by: rentals-reviewer
discovered_during: GTM-006
discovered_at: 2026-04-22
priority_hint: P1
suggested_prefix: GTM
---

## What I found

The admin SPA (`app.klikk.co.za`) relies on `window.plausible` being injected by the marketing website's `ConsentBanner.astro` consent flow. Users who navigate directly to `app.klikk.co.za` (skipping `klikk.co.za`) never trigger that consent flow, so `window.plausible` remains the stub queue and all six conversion events (`signup_completed`, `first_property_created`, `first_mandate_signed`, `first_lease_signed`, `subscription_started`) are queued but never replayed. Direct-app users — likely the majority of signups from campaign links to `/signup` — are invisible in the funnel.

## Why it matters

GTM-006's entire purpose is to make the impression → signup → paid funnel measurable. If direct-app signups are silently dropped, CAC, cohort activation rates, and per-channel conversion figures in the attribution dashboard will be understated. Campaign decisions made from incomplete data could misattribute which channels are working.

## Where I saw it

- `admin/src/plugins/plausible.ts:7–11` — the comment explicitly states "If window.plausible is not present (user arrived directly, or declined consent), all calls are silently no-oped."
- `admin/src/plugins/plausible.ts:69–80` — `initPlausible()` sets up the stub queue but nothing in the admin SPA ever loads or activates the real Plausible script.

## Suggested acceptance criteria (rough)

- [ ] Admin SPA includes its own Plausible script tag (gated behind a `/api/v1/me/consent` flag or a separate consent flow on first login)
- [ ] OR: campaign links to `/signup` route through the marketing site so consent is captured before redirect to the app
- [ ] Conversion events emitted from the admin SPA appear in Plausible for a direct-navigation test user

## Why I didn't fix it in the current task

Out of scope — GTM-006 is a documentation + consent-banner task. Fixing this requires either a server-side Plausible Events API call from Django (on account creation signals) or adding a consent mechanism to the admin SPA itself. Either path deserves its own task and a product decision on consent UX inside the app.
