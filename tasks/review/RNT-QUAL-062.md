---
id: RNT-QUAL-062
stream: rentals
title: "Document CAPACITOR_SERVER_URL in .env.development.example and README"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.1"
status: review
assigned_to: reviewer
depends_on: []
asana_gid: null
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
