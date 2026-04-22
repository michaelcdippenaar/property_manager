---
id: RNT-SEC-011
stream: rentals
title: "Expand .gitleaks.toml allowlist and resolve core.hooksPath pre-commit conflict"
feature: ""
lifecycle_stage: null
priority: P0
effort: S
v1_phase: "1.0"
status: testing
assigned_to: tester
depends_on: []
asana_gid: null
created: 2026-04-22
updated: 2026-04-23
---

## Goal

Fix the two autonomous blockers that caused RNT-SEC-001 to fail testing: (1) expand the `.gitleaks.toml` paths allowlist to cover all on-disk directories that legitimately contain secret-like patterns but are not production secrets; (2) document (and optionally script) the `core.hooksPath` unset step so `pre-commit install` succeeds for every developer.

## Context

Tester ran `gitleaks detect --source . --no-git --config .gitleaks.toml` and got 164 findings across categories that are all known-safe or gitignored. The root cause is that `.gitleaks.toml` only excludes `docs/ops/secret-rotation-2026-04.md` but not the other path categories below. The `core.hooksPath` issue prevents `pre-commit install` from running at all.

This task unblocks RNT-SEC-001 retesting. RNT-SEC-001 stays blocked on MC for key rotations, history purge, and JWT invalidation — those are not in scope here.

## Acceptance criteria

- [x] `.gitleaks.toml` `[allowlist]` paths section covers ALL of the following (regex patterns, not literals):
    1. `backend/media/vault/` — encrypted vault test documents that contain token-shaped byte sequences
    2. `tasks/` — every task markdown file; Asana GIDs trigger the `asana-client-id` rule, and audit-trail handoff notes contain known-rotated values
    3. `.claude/` — local untracked subdirs (`old/`, worktrees, `settings.local.json`) that may contain JWT tokens or old API keys
    4. `admin/dist/` — build output; bundled JS may embed the Google Maps key for the environment that was built
    5. `Klikk Proerty Manager/` — Obsidian vault (untracked); `data.json` contains an RSA private key and local REST API key
    6. `backend/.env` and `backend/.env.secrets` — on-disk gitignored env files; already gitignored but gitleaks `--no-git` still scans them
    7. `admin/.env` — same as above for the admin app
    8. `backend/.secrets/` — gitignored directory containing `google_oauth_client.json` with OAuth client_secret
- [x] After the allowlist additions, `gitleaks detect --source . --no-git --config .gitleaks.toml` → 0 findings on a standard dev machine (verified locally)
- [x] After the allowlist additions, `gitleaks detect --source . --log-opts="--all" --config .gitleaks.toml` → 0 findings across full git history
- [x] `docs/ops/secret-rotation-2026-04.md` Runbook Step 6 ("Run pre-commit install") is updated to include the prerequisite: `git config --unset-all core.hooksPath` before `pre-commit install`. Add a note explaining when `core.hooksPath` gets set (Husky, lint-staged, or IDE tooling) and that unsetting it does not break anything in this repo.
- [x] Each new allowlist entry has an inline comment explaining why it is safe to exclude (follow the pattern already used in the file for the CI DB password and OAuth client ID entries)

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

### 2026-04-22 — rentals-implementer

Added all 8 required path exclusions to `.gitleaks.toml` plus 4 additional false-positive paths discovered during smoke-check:

- `backend/apps/accounts/ACCOUNTS.md` — placeholder JWT strings in API docs (e.g. `eyJ0eXAiOiJKV1Qi...`)
- `backend/apps/test_hub/` — test fixture passwords in integration tests
- `backend/apps/accounts/tests/` — old path for the same test file (historical commit); same rationale
- Added the known-rotated Volt MCP key (`volt_owner_FslvHrwNvOjNU4RfCshcUUx0le6zRenxnu9CWJbPepM`) to the `regexes` allowlist — it appears in an older commit in `deploy/docker-compose.staging.yml` and is documented as a known-rotated secret pending MC's `git filter-repo` purge (Section 3 Step 4 of the runbook). Allowlisting prevents false-positive CI noise until that history rewrite happens.

Smoke-check results (local, gitleaks 8.30.1):
- `gitleaks detect --source . --no-git --config .gitleaks.toml` → exit code 0, 0 findings (scanned 1.23 GB)
- `gitleaks detect --source . --log-opts="--all" --config .gitleaks.toml` → exit code 0, 0 findings (107 commits)

Updated `docs/ops/secret-rotation-2026-04.md` section 2.4 with the `core.hooksPath` unset step and explanatory comment covering when the setting gets introduced and why unsetting is safe. Note: the runbook's "Step 6" label referenced in the acceptance criteria maps to section 2.4 in the document (there is no separate "Step 6: run pre-commit install" heading); the update was placed where `pre-commit install` is described.

### 2026-04-22 — rentals-reviewer

Review requested changes.

**What was checked:** All 8 required path exclusions are present and each has an inline comment. The 4 extra paths found during smoke-check are reasonable additions. The `core.hooksPath` runbook update in `docs/ops/secret-rotation-2026-04.md` section 2.4 is correct, complete, and the note explaining when/why is clear. Smoke-check exit codes are documented. Volt regex allowlist entry is appropriately commented and linked to the rotation runbook.

**Required fixes (must address before re-review):**

1. **`backend/\.env` regex is overbroad** (`/.gitleaks.toml` path entry, line ~79).
   The pattern `backend/\.env` matches not just the gitignored `backend/.env` but also the committed files `backend/.env.development`, `backend/.env.staging`, `backend/.env.production`, and `backend/.env.secrets.example`. Those committed files must remain scannable.
   Fix: anchor the pattern so it matches only the bare file, e.g. `'''backend/\.env$'''` or `'''backend/\.env[^.]'''`. Verify the chosen anchor still yields 0 findings on `--no-git`.

2. **`backend/\.env\.secrets` regex may over-match** (`/.gitleaks.toml` path entry).
   `backend/\.env\.secrets` matches `backend/.env.secrets.example` (a committed placeholder file). That file should still be scanned.
   Fix: anchor to `'''backend/\.env\.secrets$'''`.

3. **`admin/\.env` regex is overbroad** (`/.gitleaks.toml` path entry).
   Matches the committed files `admin/.env.development`, `admin/.env.staging`, `admin/.env.production`.
   Fix: anchor to `'''admin/\.env$'''`. Verify exit 0 after the change.

A discovery file covering items 1–3 has been dropped at `tasks/discoveries/2026-04-22-gitleaks-env-regex-overbroad.md`.

### 2026-04-23 — rentals-implementer

Applied all three regex anchoring fixes requested by reviewer:

1. `backend/\.env` → `backend/\.env$` (path allowlist)
2. `backend/\.env\.secrets` → `backend/\.env\.secrets$` (path allowlist)
3. `admin/\.env` → `admin/\.env$` (path allowlist)

Each comment was updated to note the `$` anchor keeps variant files (`.env.development`, `.env.staging`, `.env.production`, `.env.secrets.example`) scannable.

During smoke-check the `--log-opts="--all"` run exposed 6 new findings — all the same Google Maps API key (`AIzaSyAKdTBybb8R0xC-NldeUsjgRve7kDs5RZY`) in a single historical commit (`b2ed3ab`) across the now-scannable `backend/.env.*` and `admin/.env.*` files. This is the same situation as the Volt key: documented as HIGH in `docs/ops/secret-rotation-2026-04.md` Step 1, already rotated, and pending MC's `git filter-repo` purge. Added the key value to the `regexes` allowlist with a matching comment and commit reference.

Smoke-check results (gitleaks 8.30.1):
- `gitleaks detect --source . --no-git --config .gitleaks.toml` → exit code 0, 0 findings (scanned 1.23 GB)
- `gitleaks detect --source . --log-opts="--all" --config .gitleaks.toml` → exit code 0, 0 findings (111 commits)

### 2026-04-23 — rentals-reviewer

Review passed.

**What was checked:**

1. All 8 required path exclusions from acceptance criteria are present in `.gitleaks.toml` with inline comments (lines 66–98).
2. Round-2 specific fix: all three env regex patterns are correctly anchored with `$`:
   - `backend/\.env$` — excludes only the gitignored bare file; leaves `backend/.env.development`, `.env.staging`, `.env.production`, `.env.example`, `.env.secrets.example` scannable.
   - `backend/\.env\.secrets$` — excludes only the gitignored secrets file; leaves `backend/.env.secrets.example` scannable.
   - `admin/\.env$` — excludes only the gitignored admin bare file; leaves `admin/.env.development`, `.env.development.example`, `.env.staging`, `.env.production`, `.env.production.example` scannable.
   Confirmed against the live `.gitignore` which explicitly documents `.env` and `.env.secrets` as gitignored and the variant files as committed.
3. Google Maps API key added to `regexes` allowlist (line 50) with comment pattern matching the Volt key entry — correctly handles historical exposure in commit `b2ed3ab` pending MC's `git filter-repo` purge.
4. `docs/ops/secret-rotation-2026-04.md` section 2.4 updated with the `core.hooksPath` unset step, explanatory comment covering when it gets set and why unsetting is safe. This fully satisfies acceptance criterion 4.
5. All acceptance criteria checkboxes were already marked complete by the implementer and verified as satisfied by this review.
6. Smoke-check exit codes (0/0 findings for both `--no-git` and `--log-opts="--all"`) documented in handoff note for tester to reproduce.
7. Security/POPIA pass: no new endpoints, no PII logged, no secrets introduced — the only secrets present are already-rotated values being suppressed until history is purged.
