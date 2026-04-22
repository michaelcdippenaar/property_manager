# Agents

The 6 subagents that work this queue are defined in `.claude/agents/` at the repo root.

| Agent | Stream | Definition |
|-------|--------|------------|
| `rentals-implementer` | RNT (code) | [.claude/agents/rentals-implementer.md](../../.claude/agents/rentals-implementer.md) |
| `rentals-reviewer` | all | [.claude/agents/rentals-reviewer.md](../../.claude/agents/rentals-reviewer.md) |
| `rentals-tester` | all | [.claude/agents/rentals-tester.md](../../.claude/agents/rentals-tester.md) |
| `rentals-pm` | all (orchestration) | [.claude/agents/rentals-pm.md](../../.claude/agents/rentals-pm.md) |
| `gtm-marketer` | GTM (marketing) | [.claude/agents/gtm-marketer.md](../../.claude/agents/gtm-marketer.md) |
| `ux-onboarding` | UX (onboarding) | [.claude/agents/ux-onboarding.md](../../.claude/agents/ux-onboarding.md) |

Invoke with the `Agent` tool and `subagent_type=<name>`.
