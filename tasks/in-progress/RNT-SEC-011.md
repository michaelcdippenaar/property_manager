---
id: RNT-SEC-011
stream: rentals
title: "Expand .gitleaks.toml allowlist and resolve core.hooksPath pre-commit conflict"
feature: ""
lifecycle_stage: null
priority: P0
effort: S
v1_phase: "1.0"
status: in-progress
assigned_to: null
depends_on: []
asana_gid: null
created: 2026-04-22
updated: 2026-04-22
---

## Goal

Fix the two autonomous blockers that caused RNT-SEC-001 to fail testing: (1) expand the `.gitleaks.toml` paths allowlist to cover all on-disk directories that legitimately contain secret-like patterns but are not production secrets; (2) document (and optionally script) the `core.hooksPath` unset step so `pre-commit install` succeeds for every developer.

## Context

Tester ran `gitleaks detect --source . --no-git --config .gitleaks.toml` and got 164 findings across categories that are all known-safe or gitignored. The root cause is that `.gitleaks.toml` only excludes `docs/ops/secret-rotation-2026-04.md` but not the other path categories below. The `core.hooksPath` issue prevents `pre-commit install` from running at all.

This task unblocks RNT-SEC-001 retesting. RNT-SEC-001 stays blocked on MC for key rotations, history purge, and JWT invalidation — those are not in scope here.

## Acceptance criteria

- [ ] `.gitleaks.toml` `[allowlist]` paths section covers ALL of the following (regex patterns, not literals):
    1. `backend/media/vault/` — encrypted vault test documents that contain token-shaped byte sequences
    2. `tasks/` — every task markdown file; Asana GIDs trigger the `asana-client-id` rule, and audit-trail handoff notes contain known-rotated values
    3. `.claude/` — local untracked subdirs (`old/`, worktrees, `settings.local.json`) that may contain JWT tokens or old API keys
    4. `admin/dist/` — build output; bundled JS may embed the Google Maps key for the environment that was built
    5. `Klikk Proerty Manager/` — Obsidian vault (untracked); `data.json` contains an RSA private key and local REST API key
    6. `backend/.env` and `backend/.env.secrets` — on-disk gitignored env files; already gitignored but gitleaks `--no-git` still scans them
    7. `admin/.env` — same as above for the admin app
    8. `backend/.secrets/` — gitignored directory containing `google_oauth_client.json` with OAuth client_secret
- [ ] After the allowlist additions, `gitleaks detect --source . --no-git --config .gitleaks.toml` → 0 findings on a standard dev machine (verified locally)
- [ ] After the allowlist additions, `gitleaks detect --source . --log-opts="--all" --config .gitleaks.toml` → 0 findings across full git history
- [ ] `docs/ops/secret-rotation-2026-04.md` Runbook Step 6 ("Run pre-commit install") is updated to include the prerequisite: `git config --unset-all core.hooksPath` before `pre-commit install`. Add a note explaining when `core.hooksPath` gets set (Husky, lint-staged, or IDE tooling) and that unsetting it does not break anything in this repo.
- [ ] Each new allowlist entry has an inline comment explaining why it is safe to exclude (follow the pattern already used in the file for the CI DB password and OAuth client ID entries)

## Files likely touched

- `.gitleaks.toml`
- `docs/ops/secret-rotation-2026-04.md` (update Runbook Step 6)

## Test plan

**Manual:**
- `gitleaks detect --source . --no-git --config .gitleaks.toml` → exit code 0, 0 findings
- `gitleaks detect --source . --log-opts="--all" --config .gitleaks.toml` → exit code 0, 0 findings
- `git config --unset-all core.hooksPath && pre-commit install` → installs without error

**Automated:**
- Existing CI gitleaks job (`.github/workflows/ci.yml`) will pick up the updated `.gitleaks.toml` automatically; confirm the job passes on the PR for this task

## Handoff notes

(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

### 2026-04-22 — rentals-pm

Split from RNT-SEC-001 blocked triage. The tester identified two autonomous failure categories: incomplete `.gitleaks.toml` paths allowlist and `core.hooksPath` blocking `pre-commit install`. These are fully code-and-config changes requiring no production access. Once this task is done and merged, RNT-SEC-001 can be re-tested against its remaining MC-gated criteria.
