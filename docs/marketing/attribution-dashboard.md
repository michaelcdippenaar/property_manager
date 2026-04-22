# Klikk Marketing Attribution Dashboard

_Last updated: 2026-04-22. This document describes the analytics stack, conversion events, per-channel dashboard, cohort view, and weekly review ritual for Klikk Rentals v1 launch._

---

## Analytics stack

### Decision: Plausible (self-hosted)

Klikk uses **Plausible Analytics** — self-hosted — as the primary analytics tool for both marketing (website) and product funnel tracking.

Reasons for choosing Plausible over PostHog:
- Privacy-first by design: no cookies, no cross-site tracking, GDPR/POPIA aligned out of the box
- No consent banner required for page views (cookie-less); the existing banner covers the optional custom-event tracking
- Self-hosted on the same VPS as the Django backend — all data stays in South Africa, satisfying POPIA s72 data localisation guidance
- Single script tag, no SDK overhead, tiny payload
- Built-in UTM parameter tracking, custom goals, and funnel views

PostHog remains the recommended choice if session recordings or deeper product analytics become necessary in v2. The two are complementary, not exclusive.

### Data residency

Self-hosted instance on `af-south-1` (Cape Town) AWS region or the existing production VPS in ZA. No data is sent to Plausible Cloud EU/US. This satisfies POPIA s72 on cross-border transfers.

---

## Analytics script installation

### Website (Astro)

The Plausible script is added to `website/src/layouts/BaseLayout.astro` inside `<head>`, deferred, and gated behind consent:

```html
<!-- Plausible Analytics — loaded only after consent accepted -->
<!-- Script injected by ConsentBanner.astro after klikk_consent=analytics -->
<script id="plausible-placeholder" data-domain="klikk.co.za" data-deferred="true"></script>
```

The ConsentBanner activates the script on accept (see `website/src/components/ConsentBanner.astro`).

### Admin SPA (Vue 3)

Plausible custom events are emitted from `admin/src/main.ts` via a lightweight wrapper:

```ts
// Usage: plausible('signup_completed', { props: { plan: 'free' } })
```

The wrapper checks `window.plausible` (injected by the script tag) before calling — gracefully no-ops if consent was not given or script is not loaded.

### In-app event catalogue

| Event name | Where fired | Props |
|-----------|-------------|-------|
| `signup_started` | Sign-up page: form first-touched | `plan: 'free' \| 'pro' \| 'agency'` |
| `signup_completed` | After successful account creation | `plan`, `source: utm_source if present` |
| `first_property_created` | After first property is saved | — |
| `first_mandate_signed` | After first mandate e-signed | — |
| `first_lease_signed` | After first lease e-signed | — |
| `subscription_started` | After successful Stripe/PayFast payment | `plan`, `mrr_zar` |

These events are emitted server-side (Django signal → Plausible Events API) as well as client-side, so that server-side conversions are captured even if the browser script is blocked.

---

## POPIA compliance

- Plausible page views: **no consent required** — no cookies, no PI collected
- Custom events (signup funnel): consent required — fired only after `klikk_consent=analytics` is set
- The existing `ConsentBanner.astro` covers this; the "Essential only" path must not emit any custom events
- No PI (email, name, IP) is passed in any event property — `plausible()` calls use only anonymous labels
- The Privacy Policy at `/legal/popia` is updated to reference Plausible self-hosted analytics

---

## Per-channel dashboard

Reviewed weekly on Monday morning (see Weekly Review Ritual below).

### Dimensions tracked per channel

| Metric | How measured |
|--------|-------------|
| Impressions | Platform native (LinkedIn Analytics, Meta Business Suite) — logged manually in the weekly review sheet |
| Clicks to site | Plausible → Visits filtered by `utm_source` |
| Signups | Plausible `signup_completed` event by `utm_source` |
| Activations | Plausible `first_property_created` event (joined by visitor ID via Plausible Funnels) |
| Paid conversions | `subscription_started` event |
| CAC (Customer Acquisition Cost) | Manual: channel spend ÷ paid conversions from that channel |
| Payback period | Manual: CAC ÷ monthly MRR per customer |

### Channel breakdown table (template — populate weekly)

| Channel | utm_source | Visits | Signups | Activations | Paid | Spend (ZAR) | CAC (ZAR) |
|---------|-----------|--------|---------|-------------|------|-------------|-----------|
| LinkedIn organic | `linkedin` | — | — | — | — | R0 | — |
| Facebook groups | `facebook` | — | — | — | — | R0 | — |
| Email (warm network) | `email` | — | — | — | — | R0 | — |
| PR (Business Insider) | `business_insider` | — | — | — | — | R0 | — |
| PR (Property Professional) | `property_professional` | — | — | — | — | R0 | — |
| Webinar follow-up | `webinar` | — | — | — | — | R0 | — |
| EAAB newsletter | `eaab_newsletter` | — | — | — | — | TBC | — |
| Direct / untagged | (none) | — | — | — | — | — | — |

---

## Funnel definition

The primary conversion funnel is:

```
Website visit
  → signup_started      (form touched on /signup)
  → signup_completed    (account created)
  → first_property_created  (activated)
  → first_lease_signed  (fully onboarded — key value moment)
  → subscription_started    (paid)
```

This funnel is configured in Plausible as a Goal Funnel. The drop-off at each step is the primary diagnostic signal for the product and onboarding team.

### Conversion benchmarks (v1 assumptions)

| Stage | Assumed conversion rate | Source |
|-------|------------------------|--------|
| Visit → signup_started | 4–8% | Typical SaaS, cold traffic |
| signup_started → signup_completed | 60–75% | Form friction; improve with social login |
| signup_completed → first_property_created | 50–65% | Onboarding quality |
| first_property_created → first_lease_signed | 40–60% | Core product value moment |
| first_lease_signed → subscription_started | 10–20% | Gated by free tier limit or time |

---

## Cohort view — signup-to-activation funnel

Plausible does not natively support cohort analysis. The following approach is used until a more automated solution is available:

1. Each week, export the `signup_completed` event count with date granularity from Plausible
2. Each week, export the `first_property_created` event count
3. Map cohort: users who signed up in week W and activated in week W, W+1, W+2
4. Track in the weekly review sheet under "Cohort activation" tab

Target metric: **50%+ of sign-ups activate (add first property) within 7 days**.

If the 7-day activation rate falls below 40%, investigate:
- Is the onboarding email sequence (Sequence C) landing?
- Are users dropping off on a specific step? (Plausible funnel drop-off report)
- Is there a product friction point? (Check Sentry for errors at that step)

---

## Attribution model

### Primary: first-touch

Every signed-up account is attributed to the first `utm_source` recorded for that visitor. This is Plausible's default attribution model.

Decision rationale: At v1 with a short (days to weeks) sales cycle and a founder-led outreach strategy, first-touch tells the founder which channel surfaces the prospect. Last-touch would over-credit the "Book a demo" CTA, not the channel that put the prospect in the funnel.

### Secondary: last-touch and linear

- **Last-touch:** recorded in Plausible as the most recent `utm_source` before `signup_completed` — useful for identifying which "nudge" closes the conversion
- **Linear:** not automated in Plausible; manually estimated from visitor journeys where multiple sessions are tracked before sign-up

For v1 reporting, first-touch is the headline figure. Last-touch is a footnote. Linear is noted for future reference.

---

## Weekly review ritual

**Who:** Founder (MC) + any growth hire when applicable.
**When:** Every Monday morning, 09:00 SAST, before any outreach or content creation.
**Duration:** 20–30 minutes.
**Tool:** Plausible dashboard (self-hosted) + the weekly review sheet (Notion or Google Sheets).

### Agenda (20 minutes)

| Step | Time | Action |
|------|------|--------|
| 1 | 5 min | Open Plausible → set date range to prior week → review total visits, top sources, top pages |
| 2 | 5 min | Check funnel: signup_started → signup_completed → first_property_created → subscription_started. Note drop-off percentages. |
| 3 | 5 min | Update per-channel dashboard table with last week's numbers |
| 4 | 5 min | Flag any channel that is performing 2× above or below expectation — adjust this week's content or outreach focus accordingly |

### Weekly review questions

1. Which channel sent the most signups this week?
2. What was the signup-to-activation rate?
3. Are any paid conversions attributed to last week's campaign activity?
4. Did any channel go from zero to non-zero? (new channel working — scale it)
5. Is the Plausible goal funnel showing an unexpected drop at any step?

### Escalation rule

If `signup_completed` drops below 5 in any week after launch week, escalate immediately — check product uptime (Sentry / UptimeRobot), email deliverability (SES bounce rate), and homepage load status before assuming channel underperformance.

---

## Sentry release tagging (OPS-002 tie-in)

When a new backend or frontend release is deployed, the Sentry release name includes the campaign phase context. This allows the team to correlate funnel drop-offs with specific deployments.

Convention for `VITE_APP_RELEASE` / `SENTRY_RELEASE`:

```
klikk-admin@<semver>+<campaign-phase>
```

Examples:
- `klikk-admin@1.0.0+pre-launch` — builds deployed during pre-launch window
- `klikk-admin@1.0.1+launch-week` — hotfix during launch week
- `klikk-admin@1.1.0+post-launch-w2` — post-launch iteration

This tag appears in Sentry → Releases → and can be cross-referenced against the Plausible funnel if a deployment caused a conversion drop.

---

## Revision history

| Date | Author | Change |
|------|--------|--------|
| 2026-04-22 | gtm-marketer (GTM-006) | Initial draft — stack selection, events, dashboard template, cohort view, weekly ritual |
