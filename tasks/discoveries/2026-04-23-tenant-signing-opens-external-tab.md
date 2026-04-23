---
discovered_by: ux-onboarding
discovered_during: UX-002
discovered_at: 2026-04-23
priority_hint: P1
suggested_prefix: UX
---

## What I found
When a tenant taps "Sign Now" in `LeaseSigningView.vue`, the signing URL opens in a new browser tab via `window.open(url, '_blank')` (web) or Capacitor Browser (native). After signing, the tenant is not returned to the app — they end up in a blank tab with no path back. There is no post-signing success handler: the pending signing badge on the Home dashboard is not updated until the tenant manually refreshes.

## Why it matters
The tenant's first lease signing is the highest-stakes action in their onboarding cycle. Abandoning them in an external tab after signature creates confusion ("Did it work?"), support contacts, and delays in moving to the next onboarding step. The agent sees the signing completion via webhook, but the tenant has no confirmation in-app.

## Where I saw it
- `tenant/src/views/esigning/LeaseSigningView.vue:96-107` — opens `signing_url` in new tab; no callback or post-sign navigation
- `tenant/src/views/home/HomeView.vue:152` — `signingCta` flag only cleared on page reload, not via websocket or polling

## Suggested acceptance criteria (rough)
- [ ] After signing, the external tab redirects back to the tenant portal with a `?signed=1` query param (or similar)
- [ ] App detects the return and dismisses the signing CTA, showing a "Lease signed — awaiting countersignature" confirmation
- [ ] If a redirect back is not feasible for web, a 5-second polling loop on the signing submission after the tab is opened should suffice as a fallback

## Why I didn't fix it in the current task
Requires changes to the esigning backend redirect flow and the tenant app's post-sign state management. Out of scope for the audit task.
