# Decisions stream (`DEC-NNN`)

`DEC-NNN` tasks are **specific founder decisions** that block downstream work. They are authored as Asana tasks (assigned to MC), with a thin git mirror here so other task files can `depends_on: [DEC-NNN]`.

Each decision has:
- A clear question as the title
- Options with pros/cons
- A recommendation
- MC as assignee in Asana

MC answers in Asana (comment + mark complete). When a DEC task is answered, the `rentals-pm` agent:
1. Reads the Asana comment
2. Updates the relevant downstream task(s) with the decision (e.g. bakes the analytics provider choice into GTM-006 acceptance criteria)
3. Moves this DEC file to `done/` with the answer appended
4. Unblocks dependent tasks

## Current open decisions (v1.0)

| ID | Question | Blocks |
|---|---|---|
| DEC-001 | Analytics provider: Plausible or PostHog? | GTM-006 |
| DEC-002 | Transactional email sender: AWS SES / Mailgun / Postmark? | OPS-005 |
| DEC-003 | Production secrets vault: AWS SSM or 1Password Connect? | OPS-009 |
| DEC-004 | Uptime monitor: BetterStack / UptimeRobot / Healthchecks? | OPS-008 |
| DEC-005 | POPIA Information Officer: who's named? | OPS-004 |
| DEC-006 | Primary ICP for v1.0 launch? | GTM-001, GTM-002, UX-001 |
| DEC-007 | First-client candidate? | MIL-001 |
| DEC-008 | Launch date target for v1.0? | MIL-001, scheduling |
| DEC-009 | Pricing tiers live at launch? | OPS-007 |
| DEC-010 | Free trial length? | OPS-007 |
| DEC-011 | Tenant 2FA: required / optional / conditional? | RNT-SEC-003 |
| DEC-012 | Onboarding model for first 10 customers? | UX-001, GTM-002, MIL-001 |
| DEC-013 | Production domain scheme? | OPS-006 |
| DEC-014 | Legal reviewer for ToS / Privacy / PAIA? | OPS-004 |

All live in the **"MC Tasks"** section of the Asana project (GID `1214176966314205`), assigned to MC, and prefixed `DEC-` so they sort together. Any future DEC task authored by the PM agent goes into that section by default.
