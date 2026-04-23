# Klikk UTM Convention

_Last updated: 2026-04-22. This document is the single source of truth for all UTM parameters used across Klikk marketing. Every outbound link in website, email sequences, sales decks, and social bios MUST follow this convention._

---

## Why UTM parameters matter

Without consistent UTMs every sign-up arrives in analytics as `(direct)` — you cannot tell whether it came from a LinkedIn post, a warm-network email, or a Facebook group. GTM-006 makes the Klikk attribution loop close: impression → click → signup → activation → paid. UTMs are the thread that ties the channel to the conversion event.

---

## Five parameters, controlled vocabulary

| Parameter | Purpose | Required? |
|-----------|---------|-----------|
| `utm_source` | Where the traffic originates | Always |
| `utm_medium` | The marketing channel type | Always |
| `utm_campaign` | The specific campaign or initiative | Always |
| `utm_content` | Differentiates links within the same campaign (e.g. two CTAs in one email) | When two links in the same campaign might be clicked |
| `utm_term` | Search keyword or audience segment | Only for paid search / programmatic |

---

## utm_source — controlled values

Use only the values in this list. If your source doesn't fit, add it here rather than inventing a one-off.

| Value | When to use |
|-------|-------------|
| `linkedin` | LinkedIn posts, articles, DMs with links, events |
| `facebook` | Facebook group posts, personal profile posts |
| `email` | All email sequences (Sequence A, B, C) and one-off personal emails |
| `whatsapp` | WhatsApp messages with campaign links |
| `property_professional` | Property Professional magazine coverage or sponsored placement |
| `business_insider` | Business Insider SA coverage |
| `techcentral` | TechCentral SA coverage |
| `property360` | Property360 (IOL property) coverage |
| `mybroadband` | MyBroadband forum / AMA |
| `eaab_newsletter` | EAAB newsletter sponsorship |
| `rla_newsletter` | RLA newsletter or member communications |
| `sapoa` | SAPOA publications or events |
| `webinar` | Post-webinar follow-up emails with links |
| `referral` | User-to-user referral (when a referral programme exists) |
| `direct` | Reserved — do NOT use manually; this is what analytics assigns to untagged traffic |

---

## utm_medium — controlled values

| Value | When to use |
|-------|-------------|
| `social` | Organic social posts (LinkedIn, Facebook) |
| `email` | All email sends (warm outreach, sequences, follow-ups) |
| `pr` | Links placed in press coverage (editorial mentions, press releases) |
| `paid_social` | LinkedIn Sponsored Content, Meta Ads (if activated) |
| `paid_search` | Google Ads or Bing (not in v1 scope; reserved) |
| `newsletter` | Sponsor placements in industry newsletters (EAAB, RLA) |
| `referral` | Referral-programme links |
| `qr` | QR codes on printed/PDF assets |

---

## utm_campaign — naming convention

Format: `{phase}-{topic}-{date or version}`

| Phase prefix | Meaning |
|-------------|---------|
| `pre-launch` | Campaign activity during weeks -4 to -1 |
| `launch` | Launch week itself |
| `post-launch` | Weeks 1–4 after launch |
| `always-on` | Evergreen links in bios, footers, signature |

Examples:
- `pre-launch-founder-story-w-3` — the LinkedIn founder story post in Week -3
- `launch-announcement-email` — the launch-day email to the warm list
- `post-launch-webinar-replay` — the email distributing the webinar recording
- `always-on-homepage` — the link in the LinkedIn bio or email signature

Do NOT use spaces, capitalisation, or special characters. Hyphens only.

---

## utm_content — when to use

Use `utm_content` to distinguish two different links within the same email or post.

| Example | utm_content value |
|---------|-----------------|
| "Book a demo" CTA vs "Start free" CTA in the same email | `cta-book-demo` / `cta-start-free` |
| Top-of-email banner vs footer link | `link-header` / `link-footer` |
| Feature screenshot vs text link in a LinkedIn post | `image-cta` / `text-cta` |

---

## utm_term

Not used in v1 (no paid search). If Google Ads is activated in Month 2+, add a separate section here with keyword conventions.

---

## Link builder — quick reference

Construct links manually or use any UTM builder. Structure:

```
https://klikk.co.za/?utm_source=SOURCE&utm_medium=MEDIUM&utm_campaign=CAMPAIGN&utm_content=CONTENT
```

Examples:

| Scenario | Full UTM link |
|---------|--------------|
| Launch-day LinkedIn announcement post | `https://klikk.co.za/?utm_source=linkedin&utm_medium=social&utm_campaign=launch-announcement&utm_content=post-cta` |
| Warm-network email, "Book a demo" button | `https://klikk.co.za/demo?utm_source=email&utm_medium=email&utm_campaign=pre-launch-warm-outreach&utm_content=cta-book-demo` |
| LinkedIn bio (evergreen) | `https://klikk.co.za/?utm_source=linkedin&utm_medium=social&utm_campaign=always-on-homepage` |
| Webinar replay email, replay link | `https://klikk.co.za/demo?utm_source=webinar&utm_medium=email&utm_campaign=post-launch-webinar-replay&utm_content=cta-replay` |
| EAAB newsletter placement | `https://klikk.co.za/?utm_source=eaab_newsletter&utm_medium=newsletter&utm_campaign=post-launch-eaab-w3` |
| Sales one-pager PDF QR code | `https://klikk.co.za/demo?utm_source=email&utm_medium=qr&utm_campaign=always-on-onepager` |

---

## Attribution model (primary: first-touch)

Klikk uses **first-touch attribution** as the primary model for campaign decisions. This answers: "What was the first thing that made this person aware of Klikk?"

Rationale: at v1 launch, with a short sales cycle and a small funnel, first-touch is the most actionable signal. The founder needs to know which channel produces the first touchpoint that leads to a paid customer — not which of seven touchpoints was last.

**Last-touch** and **linear** are tracked as secondary views in the Plausible dashboard for reference. Do not optimise campaigns on last-touch at this stage.

---

## Linting and review

Before any email sequence, LinkedIn post, sales deck, or website update is published:

1. Identify every outbound link to a Klikk property (klikk.co.za, app.klikk.co.za, booking link)
2. Confirm each link has `utm_source`, `utm_medium`, and `utm_campaign`
3. Confirm parameter values match the controlled vocabulary in this document
4. If adding a new source or campaign phase, update this document first, then add the link

**Red flags to catch in review:**
- Any Klikk link without UTM parameters in a campaign-facing asset
- Spaces, capital letters, or special characters in any UTM value
- `utm_source=direct` — that value is reserved for untagged traffic
- Campaign names with dates in `YYYY/MM/DD` format — use hyphens only

---

## Revision history

| Date | Author | Change |
|------|--------|--------|
| 2026-04-22 | gtm-marketer (GTM-006) | Initial draft — controlled vocabulary, attribution model, examples |
