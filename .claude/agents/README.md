# Klikk Agent Army — Org Chart

Last updated: 2026-04-23

## Principal

**CEO (Michael Dippenaar)** — sets strategy, approves budget, signs off on marketing material before publish, reviews weekly CEO digest.

## Marketing & Sales org

```
                        ┌────────────────────────┐
                        │        CEO             │
                        │    (Michael)           │
                        └──────────┬─────────────┘
                                   │ approves budget, signs off, reviews
                                   ▼
                        ┌────────────────────────────┐
                        │ chief-marketing-officer    │◄──┐
                        │ (opus, orchestrator)       │   │ weekly digest
                        └──────────┬─────────────────┘   │
                                   │ spawns              │
         ┌───────────┬─────────────┼─────────────┬────────────┐
         ▼           ▼             ▼             ▼            ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
   │copywriter│ │  brand-  │ │analytics-│ │   user-  │ │ future:  │
   │  (opus)  │ │ creative │ │ engineer │ │researcher│ │ paid-ads │
   │          │ │ (sonnet) │ │ (sonnet) │ │  (opus)  │ │ outbound │
   │          │ │          │ │          │ │          │ │ compet-  │
   │          │ │          │ │          │ │          │ │ intel    │
   └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
        │            │            │             │
        │            │            │             │
        └────────────┴────────────┴─────────────┘
                     │ product feedback
                     ▼
             tasks/discoveries/
                     │
                     ▼ processed by
             ┌─────────────────┐
             │   rentals-pm    │ (existing)
             │   + his team    │
             └─────────────────┘
```

## Engineering org (existing, unchanged)

```
                    rentals-pm  (orchestrator)
                         │
          ┌──────────────┼──────────────┬──────────────┐
          ▼              ▼              ▼              ▼
    implementer     reviewer        tester        ux-onboarding
    (sonnet)        (sonnet)        (sonnet)      (opus)
```

## Handoff protocol

```
Marketing agent spots product issue
         │
         ▼
tasks/discoveries/<agent>-<YYYY-MM-DD>-<slug>.md
         │
         ▼ (next rentals-pm run)
rentals-pm reads inbox → promotes to RNT-NNN / UX-NNN / QA-NNN
         │
         ▼
assigned to implementer → reviewer → tester → done
         │
         ▼
feature status updated in content/product/features.yaml
         │
         ▼ (marketing agents read this on next run)
back in marketing loop
```

## Agent roster

| Agent | Model | Reports to | Owns | Primary output |
|---|---|---|---|---|
| **chief-marketing-officer** | opus | CEO | Strategy, OKRs, weekly digest, budget | `marketing/digests/` + Asana |
| **copywriter** | opus | chief-marketing-officer | All text | `marketing/blog/`, `emails/`, `social/`, `website/`, `sales/`, `campaigns/`, `lead-magnets/` |
| **brand-creative** | sonnet | chief-marketing-officer | All visual/motion | `my-video/src/`, `marketing/creative/` |
| **analytics-engineer** | sonnet | chief-marketing-officer | Measurement, funnels, UTM, experiments | `marketing/digests/<date>-dashboard.md`, `marketing/experiments.md` |
| **user-researcher** | opus | chief-marketing-officer | Qualitative VoC, surveys, interviews, Clarity | `marketing/research/voc-briefs/`, `themes.md` |

## Future hires (unlock conditions)

| Agent | Hire when… |
|---|---|
| `paid-ads-manager` | Monthly ad spend > R3k AND Plausible goals firing correctly |
| `outbound-sdr` | PBSA 30-day experiment books ≥1 demo → scale outbound |
| `competitive-intel` | Weekly competitor monitoring becomes a bottleneck (director can't keep up) |
| `content-strategist` | Content calendar > 5 pieces/week (director can't brief fast enough) |
| `sales-enablement` | Sales cycle grows past 3 active deals (demo scripts, objection docs outpace director) |

## Authority & escalation envelope

Encoded in `chief-marketing-officer.md`. Summary:

- Routine output → auto-ship
- Paid spend > R500/day → CEO approval
- Positioning / pricing change → CEO approval
- PBSA quote > R15k/month → CEO approval
- POPIA / legal risk → CEO approval
- Material for publish (blog, ad, landing page) → **CEO sign-off before publish**
- Kill an underperforming campaign → notify only

## Required skills per agent

| Agent | Existing skills | Missing (to create) |
|---|---|---|
| chief-marketing-officer | klikk-marketing-strategy, klikk-marketing-sales-enablement, klikk-marketing-competitive-intel, **klikk-marketing-orchestration** | — |
| copywriter | klikk-marketing-strategy, klikk-marketing-website | — |
| brand-creative | remotion-best-practices, **klikk-marketing-brand-assets** | — |
| analytics-engineer | **klikk-marketing-analytics** | — |
| user-researcher | **klikk-marketing-user-research** | — |
| product-documenter | klikk-platform-product-status | — |

All skills scaffolded 2026-04-23.

## Product org

```
CEO
 ├── product-documenter (sonnet) — keeps features.yaml honest, writes weekly product digest,
 │                                  changelog on every ship, plain-English CEO-readable docs
 └── support-triager (sonnet) — reads inbox/DMs, drafts replies in Klikk voice, routes
                                 bugs→rentals-pm, feature-requests→user-researcher, CEO
                                 signs off on billing/complaint/partnership replies only
```

Both report Friday digests to CEO alongside marketing digest.

## Future: graph/vector representation

This file is human-readable. Long-term plan: represent agents, handoffs, and output artefacts in a graph DB (e.g. Vault33's entity/relationship model) or a vector store for dynamic agent routing. For now: plain markdown.

Entity types:
- `agent` (chief-marketing-officer, copywriter, …)
- `artefact` (digest, dashboard, blog post, video, …)
- `metric` (CVR, reply rate, CPA, …)
- `experiment` (EXP-2026-W17-LI-01, …)

Relationships:
- `agent spawns agent`
- `agent produces artefact`
- `artefact carries metric`
- `experiment involves agent(s), targets metric`
- `agent escalates to CEO`
- `agent pushes to rentals-pm via discovery`
