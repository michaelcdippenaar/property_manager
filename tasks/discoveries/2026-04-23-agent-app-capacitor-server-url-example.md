---
discovered_by: rentals-reviewer
discovered_during: RNT-010
discovered_at: 2026-04-23
priority_hint: P2
suggested_prefix: RNT
---

## What I found
`agent-app/capacitor.config.ts:5` reads `CAPACITOR_SERVER_URL` for Capacitor live-reload during native dev, but none of the newly added `.env.*.example` files mention it. New devs who want live-reload on device have no pointer to the var.

## Why it matters
Pure DX — devs have to read `capacitor.config.ts` to discover the knob exists. The comment in that file is accurate but invisible to a new dev following the README.

## Where I saw it
- `agent-app/capacitor.config.ts:5`
- `agent-app/.env.development.example` (missing mention)

## Suggested acceptance criteria (rough)
- [ ] Add a commented `# CAPACITOR_SERVER_URL=http://<host-lan-ip>:5176` line to `.env.development.example` with a one-line explanation that it is dev-only and MUST stay unset in production
- [ ] README gets a brief "Live-reload on device" note pointing to this var

## Why I didn't fix it in the current task
Out of scope — RNT-010 ACs explicitly list only `API_URL` and `GOOGLE_CLIENT_ID` as required. Capacitor live-reload is a nice-to-have follow-up.
