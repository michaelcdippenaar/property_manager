---
name: klikk-marketing-analytics
description: >
  Plausible measurement — funnel audits, trackEvent hygiene, UTM compliance, experiment readouts.
  Loads when analytics-engineer agent runs or user asks about marketing metrics.
---

# Marketing Analytics

## Sources of truth

- **Plausible** — https://analytics.klikk.co.za (self-hosted CE, domain `klikk.co.za`)
- **Event catalogue** — `admin/src/plugins/plausible.ts` (6 goals: signup_started, signup_completed, first_property_created, first_mandate_signed, first_lease_signed, subscription_started)
- **UTM conventions** — `marketing/utm-convention.md`
- **Experiment log** — `marketing/experiments.md`
- **Dashboards** — `marketing/digests/<date>-dashboard.md`

## Weekly dashboard (Monday)

Required sections:
1. **Traffic** — uniques, source split (Google/LinkedIn/direct/referral), top 5 pages
2. **Funnel** — visitors → signup_started → signup_completed → first_property_created → first_lease_signed, absolute + step %
3. **Goal performance** — each of 6 goals, count + Δ vs prior week
4. **Source attribution** — goals split by UTM source/medium/campaign
5. **Anomalies** — anything >25% WoW
6. **Leak hypothesis** — biggest drop + why

## Benchmarks

| Step | Target |
|---|---|
| Visitor → signup_started | 10%+ |
| signup_started → signup_completed | 60%+ |
| signup_completed → first_property_created | 50%+ |
| first_property_created → first_lease_signed | 30%+ |

## Sample-size minimum

1,000 visitors/variant OR 30 conversions/variant — below that, report limitation, don't conclude.

## Event hygiene (monthly)

Grep `admin/src/` for `trackEvent` calls. Confirm each `KlikkEvent` has ≥1 call site firing on user action (not mount). Flag dead goals + orphan events to director.

## UTM compliance (weekly)

Scan top 100 Plausible sources. Flag missing `utm_campaign`, untagged linkedin.com traffic, mixed-case UTMs.

## Discovery protocol

Product-UX leaks → `tasks/discoveries/analytics-<date>-<slug>.md` with Plausible numbers. Do not fix product yourself.

## Output rules

Numbers first (tables, not prose). Before/After comparisons. No emoji. No vanity metrics without a decision attached.
