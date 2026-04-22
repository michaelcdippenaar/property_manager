# Klikk Rentals v1 — Project Hub

Single entry point for the v1.0 launch phase. Point any new agent at this file and they'll get oriented in under a minute.

## Where things live

| Thing | Location |
|---|---|
| Task queue (source of truth) | `tasks/` at repo root |
| Task workflow doc | `tasks/README.md` |
| Agent definitions | `.claude/agents/*.md` |
| Asana mirror | Workspace "Claud Projects" → project "Klikk Rentals v1" (GID `1214176966314177`) |
| Feature registry | `content/product/features.yaml` |
| Rental lifecycle | `content/product/lifecycle.yaml` |
| Brand / voice | `content/brand/` |

## How to deploy an agent

From any Claude Code session in this repo:

```
Agent(subagent_type="rentals-implementer", prompt="Work task tasks/backlog/RNT-SEC-001.md")
```

Or plain English to the orchestrator: **"Work task tasks/backlog/RNT-SEC-001.md"** — it will route.

For parallel deploys, send multiple `Agent` calls in one message. Only parallelise tasks that don't touch the same files.

### Recommended first wave (no file overlap)

1. `RNT-SEC-001` — secret rotation (P0, time-sensitive)
2. `OPS-001` — CI/CD setup
3. `GTM-007` — first-client sales kit

## v1.0 scope reminder

- **In:** 13 BUILT rentals features + hardening + ops + launch content
- **Out:** 7 PLANNED features → v2 (tenant screening, vacancy advertising, notice mgmt, incoming/outgoing inspections, deposit mgmt, deposit refund)
- **Launch gate:** `MIL-001`

## Agent roster

| Agent | Stream | Tools status |
|---|---|---|
| `rentals-implementer` | RNT / OPS / QA code | ✅ |
| `rentals-reviewer` | all code review | ✅ |
| `rentals-tester` | test execution | ⚠️ needs `mcp__tremly-e2e__*` + `mcp__Claude_Preview__*` in tools |
| `rentals-pm` | backlog + Asana sync | ⚠️ needs `mcp__10639c47-...__*` in tools |
| `gtm-marketer` | GTM stream | ✅ |
| `ux-onboarding` | UX stream | ⚠️ needs `mcp__Claude_Preview__*` + `mcp__tremly-e2e__*` in tools |

Fixes tracked in `skill-audit.md` (this folder).

## Open decisions blocking work

- `DEC-007` — first-client candidate (MC to name agency)
- `RNT-009` open question — does Quasar tenant PWA project exist, or needs Vue→Quasar migration first?
