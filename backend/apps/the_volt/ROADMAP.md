# The Volt — Roadmap

> The Volt is a user-owned data sovereignty vault: encrypted per-owner storage
> of entity data (personal, company, trust, CC, sole prop, asset) with POPIA-native
> consent, checkout, and audit. Built inside the Klikk monorepo; designed to ship
> as a standalone product later.

---

## Contract boundary — read this first

- **Public API** (stable, versioned): `/api/v1/the-volt/gateway/*`
- **Internal API** (used by Klikk apps, stable-with-deprecation): `InternalGatewayService`
- **Internals** (churn freely): `owners/`, `entities/`, `documents/`, `encryption/`, `schemas/`, `packages/`, `mcp/`

Klikk apps **must not** import directly from Volt internals. Import-boundary
CI check to be added in Phase 7.

---

## Status

**Phase 1 — Core vault (COMPLETE 2026-04-15)**

- [x] Module skeleton (`owners/`, `entities/`, `documents/`, `encryption/`, `gateway/`, `schemas/`)
- [x] Per-owner Fernet encryption at rest
- [x] OTP-based owner approval flow (`DataRequestApprovalLink`)
- [x] Hybrid graph+vector queries (`VaultQueryService`)
- [x] `InternalGatewayService` (no-FK data sovereignty)
- [x] ChromaDB RAG helpers (`core/volt_rag.py`)
- [x] Client-supplied OCR JSON pipeline (no server-side extraction)
- [x] Verification layer: `DocumentVerification` + `EntityDataField`
- [x] Certified copy encrypted storage (commissioner-of-oaths signed copies)
- [x] Migrations `0001` + `0002` applied
- [x] Admin registered for all models

---

## Phase 2 — First import path (Claude CoWork → Gmail/Drive → Volt) — IN PROGRESS

**Goal:** owner can import owner/property/tenant data from Gmail + Drive into
the Volt via Claude CoWork, end to end.

### 2.1 — Document Catalogue + Ownership Scope

- [ ] `DocumentTypeCatalogue` model
  - fields: `code`, `label`, `entity_type`, `ownership_scope`, `issuing_authority`,
    `default_validity_days`, `email_sender_patterns[]`, `email_subject_patterns[]`,
    `regulatory_reference`, `is_active`, `sort_order`
  - `OwnershipScope`: `asset_bound` | `owner_bound` | `shared`
- [ ] Migration scaffolding (empty data)
- [ ] Seed data migration — ~85 SA documents (Sonnet task)
  - Personal (18), Company (20), Trust (13), CC (9), Sole Prop (9)
  - Asset-Property (20), Asset-Vehicle (6), Asset-Financial (5), Asset-Movable (3)
- [ ] Keep existing `DocumentType` TextChoices as an alias layer; FK migration deferred to 2.4

### 2.2 — Resource Package Templates

- [ ] `ResourcePackageTemplate` model
  - fields: `code`, `country_code`, `entity_type`, `version`, `label`,
    `required_documents[]`, `required_fields[]`, `optional_*[]`,
    `max_age_days{}`, `regulatory_basis`, `is_active`
- [ ] Seeded packs (v1, ZA):
  - `fica` (personal / company / trust)
  - `rental_application` (personal)
  - `home_loan` (personal)
  - `property_sale` (personal + asset)
  - `property_rental_landlord` (personal + asset)
  - `procurement` (company / trust)
  - `estate_planning` (personal)
- [ ] `resolve_package(entity, code) → manifest` completeness engine
- [ ] MCP tool: `check_package`, `list_available_packages`

### 2.3 — Owner-scoped API keys + MCP server

- [ ] `VaultOwnerAPIKey` model (`vault_owner`, `api_key_hash`, `api_key_prefix`, `label`, `is_active`, `last_used_at`)
- [ ] `VoltOwnerApiKeyAuthentication` DRF class (parallel to subscriber auth)
- [ ] `apps/the_volt/mcp/` package — FastMCP server mounted at `/mcp/`
- [ ] Read tools: `find_entity`, `list_entities`, `get_entity`, `list_documents`
- [ ] Write tools: `ensure_vault`, `upsert_owner`, `upsert_property`, `upsert_tenant`,
  `attach_document`, `link_entities`
- [ ] `VaultWriteAudit` model — one row per MCP mutation
- [ ] Add `LEASES_FROM`, `PARENT_OF` to `RelationshipType`
- [ ] Setup doc: connecting claude.ai Gmail + Drive + Volt MCP
- [ ] Run first real import end-to-end (landlord → property → tenant → lease)

### 2.4 — Catalogue FK migration (after seed is stable)

- [ ] Migrate `VaultDocument.document_type` from TextChoices → FK to `DocumentTypeCatalogue`
- [ ] Update serializers, admin, views

---

## Phase 3 — Requester validation + per-item requests (POPIA §11 + §18)

- [ ] `RequesterProfile` refactor: `DataSubscriber` → OneToOne with `VaultEntity`
- [ ] `DataRequestItem` model (per-item justification + legal basis + retention)
- [ ] Requester onboarding flow (must file their own FICA pack before requesting)
- [ ] Verification symmetry rule (can't demand tier higher than you hold)
- [ ] Retention ceilings by legal basis (consent 12mo, contract 5yr, etc.)
- [ ] Per-item approval UI on public approval page

---

## Phase 4 — Gateway evolution (checkout = release event)

- [ ] `DataCheckout.item_fingerprints` per-item hash snapshot
- [ ] `POST /gateway/checkout/{token}/refresh/` — delta response (value_changed, document_new_version, verification_upgraded, expired, revoked)
- [ ] `POST /gateway/checkout/{token}/verify/` — integrity echo (free, cheap)
- [ ] `GET /gateway/checkout/{token}/status/` — active | revoked | superseded
- [ ] `CheckoutUpdateNotification` signal on `DocumentVersion` / `EntityDataField` saves
- [ ] `DestructionReceipt` model + `POST /gateway/checkout/{token}/destruction-receipt/`
- [ ] Owner dashboard: "outstanding checkouts" with revoke + ack status

---

## Phase 5 — Paid tier metering

- [ ] `RequesterProfile.subscription_tier` + quota fields
- [ ] `CheckoutRefreshMeter` model (one row per refresh for billing rollup)
- [ ] Refresh quota enforcement middleware
- [ ] `402 Payment Required` on over-quota standing grants
- [ ] `410 Gone` on lost-base refresh attempts (with owner notification)

---

## Phase 6 — Asset transfer flow

- [ ] `VaultEntity.transferred_to_vault_id` + `transferred_at` + `transfer_reason`
- [ ] `transfer_asset` MCP tool (sale / inheritance / donation)
- [ ] Property Sale Transfer pack (pre-selects `asset_bound` docs)
- [ ] Re-encryption pipeline: decrypt with seller key → re-encrypt with buyer key
- [ ] Seller's entity archived (is_active=False) but retained for statutory period

---

## Phase 7 — Productisation as standalone

- [ ] Product name + brand identity
- [ ] Public OpenAPI spec, separate from Klikk docs
- [ ] Import-boundary CI check (Klikk apps must not import Volt internals)
- [ ] Minimal marketing page at `volt.klikk.co.za`
- [ ] Versioned gateway (`/api/v1/` stable; `/api/v2/` for breaking changes)
- [ ] POPIA-focused FAQ + sample audit receipt

---

## Architectural Decisions (session 2026-04-15)

1. **No FK between Klikk and Volt** — access via `InternalGatewayService` only.
2. **Client-supplied OCR** — no server-side AI extraction; client sends parsed JSON + file.
3. **Every requester is a VaultEntity** — no faceless subscribers with just API keys.
4. **Checkout = release event, not session** — subscribers hold local copies.
5. **Standing grants = repeat-checkout quota** — not continuous polling.
6. **Delta refreshes** — on standing grants, return only changed items. Five delta types.
7. **Refreshes are paid; revocation notifications are free** — POPIA safety first.
8. **Lost data → consent reset** — 410 Gone; vault never backs up for subscribers.
9. **Per-item justification + legal basis + retention** — POPIA §11 / §18 by construction.
10. **Verification symmetry** — requester must hold tier ≥ what they demand.
11. **`ownership_scope` on documents** — `asset_bound` transfers with asset; `owner_bound` stays; `shared` dual-vaulted.
12. **Document catalogue is data, not TextChoices** — regulatory changes are data migrations.
13. **Retention ceiling from original consent** — deltas can shorten, never extend.
14. **MCP surfaces are distinct** — owner's Volt MCP is live; subscribers run their own MCP off local checkout cache.
15. **Cross-vault entity identity = references, not shared tables** — one canonical copy per vault.
16. **Shared docs** — each party vaults own encrypted copy, linked via `source_artefact_id`; oldest ingest timestamp = source of truth if hashes match.

---

## Deferred / Out of scope for v1

- Server-side AI extraction
- HSM / KMS key rotation (Fernet per-owner suffices for v1)
- Multi-country schemas (ZA only for v1)
- Neo4j graph upgrade (ORM handles ≤ 3 hops fine)
- Cross-vault canonical entity identity
- Shared-secret encryption for joint-custody documents
- Dedicated `klikk-volt-*` Claude skill (revisit when product has external customers)

---

## How we work on this module

**Models:**
- Opus 4.6 — architectural design, POPIA interpretation, tricky migrations
- Sonnet 4.6 (`/fast`) — bulk model / migration / tool coding, seed data
- Haiku 4.5 (via `Explore quick`) — file / symbol lookups

**Subagents:**
- `Explore` — existing Klikk code that will eventually migrate into Volt
- `Plan` — tricky data migrations (Phase 2 Person→VaultEntity backfill, Phase 6 re-encryption flow)
- `general-purpose` — bulk research (e.g. SA municipality rates-clearance document naming patterns)

**Skills in the repo we'll invoke:**
- `klikk-documents-owner-cipro` — SA owner/landlord doc classification (high overlap with `DocumentTypeCatalogue`)
- `klikk-security-api-review` — review `/mcp/` before exposing publicly
- `klikk-security-compliance` — POPIA gate check before each phase merges
- `klikk-platform-testing` — write vault tests
- `klikk-platform-product-status` — update `content/product/features.yaml` when phases ship
