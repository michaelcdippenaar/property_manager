# POPIA Compliance Brief — Klikk Rentals

*Generated 2026-05-06 to inform multi-tenant rollout (Phase 1 schema design). Combines the existing `vault33-popia-ruleset` skill with current public POPIA + 2025/2026 amendments. See `~/.claude/plans/fuzzy-giggling-squid.md` for the rollout plan this informs.*

## TL;DR — what changes Phase 1 schema

Each per-tenant model gets, in addition to the planned `agency_id` FK:

| Field | Why | Models |
|---|---|---|
| `lawful_basis` (CharField with choices) | s11 — every PI record needs declared basis (`consent` / `contract` / `legal_obligation` / `legitimate_interest`) | All PI-bearing models (Person, Landlord, Lease, MaintenanceRequest, Supplier, etc.) |
| `vault_entity_id` (PositiveIntegerField, nullable) | Phase 2 prep — Vault33 will be the cross-agency identity layer; adding now is free, adding later is a data migration | Person, User, Landlord, Supplier |
| `retention_policy` (CharField with choices) | s14 — disposal obligation; choices: `lease_lifetime`, `7yr_fica`, `5yr_fica`, `3yr_rha`, `90day_ai_chat`, `permanent_audit` | All PI-bearing models |
| `is_anonymised` (bool) + `anonymised_at` + `anonymisation_reason` | s23/s24/s25 DSAR support; signed leases can't be hard-deleted, must anonymise surrounding PI | Person, User, Landlord, Supplier |
| `agency_id` FK on **AuditEvent** | Critical isolation gap — agency A must never query agency B's audit trail | AuditEvent |

These additions cost ~5 fields per model. Adding them in the **same migration** as `agency_id` means one migration pass, not two. Skip them now and we ship a known-broken POPIA posture that needs a second migration sweep within months.

## Roles

- **Each agency** is the *responsible party (RP)* for its tenants', landlords', and suppliers' PI.
- **Klikk** is the *operator* under s21 — processes only on agency instruction.
- **Sub-operators** (Anthropic, AWS SES, Plausible, Sentry) need DPAs on file. Anthropic is US-based — every AI prompt that includes a tenant name/ID/address is a s72 cross-border transfer.

## What Phase 1 must cover (schema-level)

1. **Lawful basis stamped at record creation** (s11)
2. **Per-agency audit trail** (s19) — `AuditEvent.agency_id` is non-negotiable
3. **DSAR-friendly soft-delete** — `is_anonymised` + `anonymised_at` instead of hard delete; lease PDFs can never hard-delete (RHA + FICA retention)
4. **Vault33 placeholder FKs** — `vault_entity_id` on identity models so Phase 2 sharing is a data backfill, not a migration
5. **Retention policy enum** — informational in Phase 1; a cron job in a later phase reads it to anonymise expired records

## What Phase 1 explicitly does NOT cover (deferred)

- `BreachIncident` model + 72h notification pipeline (s22) → Phase 2.5
- Cross-border processing record (`CrossBorderTransferRecord` or per-record `cross_border_processed` flag) → Phase 2 alongside AI-guide audit
- Retention cron + automated anonymisation → Phase 2.5
- Per-subject DSAR export endpoint → Phase 3
- `revoked_at` + `basis_evidence` on `UserConsent` → small follow-up commit, NOT in Phase 1's main migration sweep
- Field-level encryption for `id_number` / `date_of_birth` → security sprint, not POPIA-blocking

## Risks if we ship Phase 1 isolation WITHOUT these schema fields

1. **No lawful basis on any PI record** — direct s11 violation, exposed by any DSAR. (Information Regulator fined WhatsApp Sept 2024 for s8/s9/s11 failures.)
2. **AuditEvent leaks across agencies** — both an IDOR (s19) and a disclosure (s8) violation.
3. **Cross-border transfers undocumented** — every AI-routed prompt invisibly crosses to Anthropic US.
4. **No retention enforcement** — accumulated chat logs and stale lease metadata become unbounded liability.
5. **Hard-delete on tenant request** breaks RHA/FICA retention obligations; soft-delete with `is_anonymised` is the only safe default.

## Top sources cited

- POPIA 2025 Amendment Regulations GG 52523 (s11 consent tightening, s72 cross-border)
- POPIA s11 (lawful processing), s14 (retention), s19 (security), s22 (breach), s23/24/25 (DSARs), s72 (cross-border)
- Information Regulator enforcement: WhatsApp (Sept 2024), IEC (2024)
- Vault33 POPIA ruleset skill (`~/.claude/skills/vault33-popia-ruleset/`)

## Vault33 migration path (key insight)

Klikk's per-agency Person/Landlord/Supplier rows in Phase 1 are *temporary* identity records. In Phase 2, Vault33 becomes the single source of truth for human/legal-entity identity, and Klikk records become *projections* tied to a `vault_entity_id`. As long as that FK exists from day 1, the migration is a data backfill, not a schema change.

This means: agencies that join Vault33 later don't lose data, and tenants who move from agency A to agency B can carry their identity (with consent) without Klikk ever sharing data directly between agencies.
