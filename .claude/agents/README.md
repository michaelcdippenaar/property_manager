# Klikk Agent Army — Org Chart

Last updated: 2026-04-23

## Principal

**CEO (Michael Dippenaar)** — sets strategy, approves budget, signs off on marketing material before publish, reviews weekly CEO digest.

```
                         ┌──────────────────────────┐
                         │        CEO (MC)          │
                         │     mc@tremly.com        │
                         │   Landlord + Founder     │
                         └──────┬──────────┬────────┘
                                │          │
               ┌────────────────┤          ├────────────────────┐
               │                │          │                    │
       ┌───────▼──────┐  ┌──────▼───────┐  │           ┌────────▼───────┐
       │     CTO      │  │     CMO      │  │           │ support-       │
       │   (opus)     │  │   (opus)     │  │           │ triager        │
       │ Launch rev,  │  │ Weekly OKRs, │  │           │ (sonnet)       │
       │ risk reg,    │  │ CEO digest,  │  │           │ Inbox, SLA<4h  │
       │ design calls │  │ ICP strategy │  │           │ (dormant S0)   │
       └───────┬──────┘  └──────┬───────┘  │           └────────────────┘
               │                │          │
               ▼                ▼          ▼
    ┌─────────────────┐  ┌──────────────────────────────────────────┐
    │    AUTOPILOT    │  │           MARKETING & GTM                │
    │ (file-based     │  │                                          │
    │  task queue)    │  │  • chief-marketing-officer (orchestrator)│
    │                 │  │  • gtm-marketer                          │
    │  tasks/         │  │  • copywriter                            │
    │   backlog/      │  │  • brand-creative                        │
    │   in-progress/  │  │  • analytics-engineer  (Plausible)       │
    │   review/       │  │  • user-researcher     (VoC, NPS)        │
    │   testing/      │  │  • product-documenter  (features.yaml)   │
    │   blocked/      │  └──────────────────────────────────────────┘
    │   done/         │
    │   discoveries/  │
    └────────┬────────┘
             │
┌────────────┼───────────────┬──────────────┬─────────────┐
▼            ▼               ▼              ▼             ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐
│rentals-  │ │rentals-  │ │rentals-  │ │rentals-  │ │   ux-      │
│pm        │ │implement │ │reviewer  │ │tester    │ │onboarding  │
│          │ │er        │ │(opus)    │ │          │ │            │
│Triage,   │ │Writes    │ │Reviews   │ │pytest +  │ │Onboarding  │
│Asana     │ │code,     │ │diffs,    │ │E2E MCP,  │ │flows, in-  │
│sync,     │ │commits,  │ │bounces   │ │Claude    │ │app tuts,   │
│blocked   │ │hands off │ │or ships  │ │Preview   │ │training    │
│triage    │ │          │ │to test   │ │          │ │videos      │
└──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────────┘

Parallel caps: 3 implementers + 1 reviewer + 1 tester
Reviewer on Opus; implementers/testers on Sonnet/Haiku
```

## Agent roster

| Agent | Model | Reports to | Owns | Primary output |
|---|---|---|---|---|
| **cto** | opus | CEO | Launch review, risk register, design calls | Risk register, architecture decisions |
| **chief-marketing-officer** | opus | CEO | Strategy, OKRs, weekly digest, budget | `marketing/digests/` + Asana |
| **support-triager** | sonnet | CEO | Inbox SLA <4h (dormant Stage 0) | `marketing/support/drafts/` |
| **gtm-marketer** | sonnet | CMO | Go-to-market execution, launch campaigns | `marketing/campaigns/`, `marketing/website/` |
| **copywriter** | opus | CMO | All text content | `marketing/blog/`, `emails/`, `social/`, `sales/` |
| **brand-creative** | sonnet | CMO | All visual/motion | `my-video/src/`, `marketing/creative/` |
| **analytics-engineer** | sonnet | CMO | Plausible, funnels, UTM, experiments | `marketing/digests/<date>-dashboard.md` |
| **user-researcher** | opus | CMO | Qualitative VoC, surveys, NPS, Clarity | `marketing/research/voc-briefs/` |
| **product-documenter** | sonnet | CMO | features.yaml honesty, CEO-readable docs | `content/product/features.yaml`, `content/changelog/` |
| **rentals-pm** | opus | CTO/Autopilot | Engineering triage, Asana sync, blocked triage | Task files, Asana |
| **rentals-implementer** | sonnet/haiku | rentals-pm | Writes code, commits, hands off | Code commits |
| **rentals-reviewer** | opus | rentals-pm | Reviews diffs, bounces or ships to test | Review decisions |
| **rentals-tester** | sonnet | rentals-pm | pytest + E2E MCP, Claude Preview | Test results |
| **ux-onboarding** | opus | rentals-pm | Onboarding flows, in-app tutorials, training videos | UX specs, tutorial content |

## Handoff protocol

```
Marketing / Support agent spots product issue
         │
         ▼
tasks/discoveries/<agent>-<YYYY-MM-DD>-<slug>.md
         │
         ▼ (next rentals-pm run via Autopilot)
rentals-pm reads inbox → promotes to RNT-NNN / UX-NNN / QA-NNN
         │
         ▼
implementer → reviewer → tester → done
         │
         ▼
product-documenter updates content/product/features.yaml (status: BUILT)
         │
         ▼
CMO picks up new feature → clears for use in copy
```

## Stage 0 active agents (right now)

Only these agents have active work in Asana today:

| Agent | Active task |
|---|---|
| **CEO** | Identify T1–T4 beta peers (personal network) |
| **CMO** | Value-prop one-liners per ICP segment |
| **copywriter** | T2/T3 lead magnet drafts |
| **analytics-engineer** | Plausible UTM conventions doc |
| **rentals team** | App → testing-ready (hard gate for beta) |

Dormant until Stage 1: support-triager, paid-ads-manager, outbound-sdr, competitive-intel.

## Authority & escalation envelope

Encoded in `chief-marketing-officer.md`. Summary:

- Routine output → auto-ship (CEO signs off before publish)
- Paid spend > R500/day → CEO approval
- Positioning / pricing change → CEO approval
- PBSA quote > R15k/month → CEO approval
- POPIA / legal risk → CEO approval
- Kill an underperforming campaign → notify only

## Required skills per agent

| Agent | Skills |
|---|---|
| chief-marketing-officer | klikk-marketing-strategy, klikk-marketing-sales-enablement, klikk-marketing-competitive-intel, klikk-marketing-orchestration |
| copywriter | klikk-marketing-strategy, klikk-marketing-website |
| brand-creative | remotion-best-practices, klikk-marketing-brand-assets |
| analytics-engineer | klikk-marketing-analytics |
| user-researcher | klikk-marketing-user-research |
| product-documenter | klikk-platform-product-status |

## Future hires (unlock gates)

| Agent | Hire when… |
|---|---|
| `paid-ads-manager` | Monthly ad spend > R3k AND Plausible goals firing correctly |
| `outbound-sdr` | PBSA 30-day experiment books ≥1 demo → scale outbound |
| `competitive-intel` | CMO can't keep up weekly monitoring |
| `content-strategist` | Content calendar > 5 pieces/week |
| `sales-enablement` | Sales cycle grows past 3 active deals |

## Future: graph/vector representation

Long-term: represent agents, handoffs, artefacts in Vault33 graph DB. For now: plain markdown.

Entity types: `agent`, `artefact`, `metric`, `experiment`

Relationships: `agent spawns agent`, `agent produces artefact`, `artefact carries metric`, `experiment targets metric`, `agent escalates to CEO`, `agent pushes to rentals-pm via discovery`
