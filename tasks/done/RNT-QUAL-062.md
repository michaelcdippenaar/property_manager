---
id: RNT-QUAL-062
stream: rentals
title: "Document CAPACITOR_SERVER_URL in .env.development.example and README"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.1"
status: done
assigned_to: null
depends_on: []
asana_gid: "1214275337455872"
created: 2026-04-24
updated: 2026-04-24
---

## Goal
Ensure new developers can discover and configure `CAPACITOR_SERVER_URL` for live-reload on device without having to read `capacitor.config.ts` directly.

## Acceptance criteria
- [x] `agent-app/.env.development.example` includes a commented line `# CAPACITOR_SERVER_URL=http://<host-lan-ip>:5176` with a note that it is dev-only and must NOT be set in production
- [x] `agent-app/README.md` (or top-level README) includes a brief "Live-reload on device" section pointing to the variable

## Files likely touched
- `agent-app/.env.development.example`
- `agent-app/README.md` (or root `README.md`)

## Test plan
**Manual:**
- Follow the README instructions as a new developer; confirm `CAPACITOR_SERVER_URL` is discoverable without reading source files

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-24 — Promoted from discovery `2026-04-23-agent-app-capacitor-server-url-example.md`. Pure DX improvement; deferred to v1.1 as non-blocking.

2026-04-24 — implementer: Added commented `CAPACITOR_SERVER_URL` block to `agent-app/.env.development.example` (with dev-only warning). Added "Live-reload on device" section to `agent-app/README.md` with step-by-step instructions and a production-safety warning. Also added the variable to the Environment Variables table in the README. No code touched.

2026-04-24 — Review passed. Checked `.env.development.example` line 17 (commented entry + dev-only/prod-safety warning present) and `agent-app/README.md` lines 35-54 (Live-reload section with steps + Env Vars table entry). Both acceptance criteria satisfied. No code risk; no auth/POPIA surface. Approved.

2026-04-24 — tester: All checks pass. (1) `.env.development.example` line 16 carries "DEV ONLY — must NOT be set in staging or production builds", line 17 has commented `CAPACITOR_SERVER_URL=` entry. (2) `agent-app/README.md` line 35 "Live-reload on device" section present with steps and prod-safety warning; line 54 Env Vars table row present. (3) `git show HEAD -- agent-app/` produced no output — no .ts/.vue code touched. All acceptance criteria satisfied.
