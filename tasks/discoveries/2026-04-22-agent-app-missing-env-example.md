---
discovered_by: rentals-reviewer
discovered_during: RNT-SEC-001
discovered_at: 2026-04-22
priority_hint: P2
suggested_prefix: RNT
---

## What I found

`agent-app/` has no `.env*.example` files. After RNT-SEC-001 removed the real `GOOGLE_CLIENT_ID` value from `agent-app/.env.development`, there is no documented reference for what env vars the agent-app needs on a fresh checkout.

## Why it matters

A developer (or CI pipeline) setting up the agent-app locally has no checklist of required env vars. `GOOGLE_CLIENT_ID` is now undocumented for this app, and any future secrets added will have the same gap. The `admin/` app has `admin/.env.development.example` and `admin/.env.production.example` — agent-app should follow the same pattern.

## Where I saw it

- `agent-app/.env.development` — `GOOGLE_CLIENT_ID` comment only, no example file exists
- `admin/.env.development.example` — exists and documents vars correctly (the pattern to follow)
- `ls agent-app/.env*.example` → no matches

## Suggested acceptance criteria (rough)
- [ ] Add `agent-app/.env.development.example` listing `API_URL` and `GOOGLE_CLIENT_ID` with placeholder values and a comment pointing to `.env.secrets`
- [ ] Add `agent-app/.env.production.example` and `agent-app/.env.staging.example` (or a single `agent-app/.env.example`) with the same vars

## Why I didn't fix it in the current task

Out of scope for RNT-SEC-001, which focused on removing existing secrets. This is a developer-experience hardening follow-up.
