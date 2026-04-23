# Vault33 — App Overview

> Last updated: 2026-04-18. For competitive context see `competitors.md`.

## What It Is

Vault33 is a **single-tenant, encrypted personal-data vault** — the compliance infrastructure layer for South African property managers. It is a **separate product** from Klikk Rentals, running in its own Django project (`/PycharmProjects/vault33/`), but deeply integrated with the Klikk platform via a bridge client.

It handles three SA regulatory frameworks:
- **POPIA** — consent, data minimisation, breach notification, DSAR
- **FICA** — beneficial ownership verification, 5-year retention, KYC
- **RHA** — deposit records, inspection photos, communication logs

---

## Core Problem It Solves

Before a property manager can sign a lease or share a tenant's data with a bank, conveyancer, or SARS, they must:
1. Store identity documents securely and prove they haven't been tampered with
2. Map and prove beneficial ownership chains (FICA §21A)
3. Share data with third parties compliantly — consent-gated, audited, time-limited

No existing SA product covers all three for the property management context. Vault33 does.

---

## What It Stores

### Entities (6 types)
People, companies, trusts, close corporations, sole proprietors, and assets — each with a unique SA identity key (id_number, reg_number, trust_number).

### Relationship Graph (10 types)
`director_of`, `trustee_of`, `beneficial_owner_of`, `shareholder_of`, `member_of`, `holds_asset`, `operates_as`, `guarantor_for`, `leases_from`, `parent_of`

Multi-hop beneficial ownership chain traversal — meets FICA §21A BO register requirements.

### Documents (~85 SA-specific types)
Smart ID, Passport, CoR14.3, Trust Deed, Title Deed, Letters of Authority, bank statements, SARS docs, insurance, rates clearance, etc. Versioned, Fernet-encrypted at rest. Each field tracks verification status from `UNVERIFIED` through to `OFFICIAL_SOURCE`.

---

## How It Works

### Encryption
Fernet at rest with a per-owner PBKDF2-HMAC-SHA256 key (100k iterations). Every write is logged in an append-only `VaultWriteAudit`.

### Consent Gateway
Third party requests data → 6-digit OTP sent via SMS (Twilio) to vault owner → owner approves via admin SPA or public link → `CheckoutService` packages + HMAC-SHA256 signs → immutable `DataCheckout` record. Delivery: REST (inline) or MCP (manifest + separate fetch endpoint).

### AI Interface
23 MCP tools (10 read + 13 write). Works with Claude Desktop, Claude Code, and any MCP-compatible LLM client. This is a unique competitive advantage — no other SA compliance platform has an AI-native interface.

---

## Current State (2026-04-18)

| Area | Status |
|---|---|
| Models, REST API | BUILT |
| MCP server (23 tools) | BUILT |
| Fernet encryption + audit | BUILT |
| Gateway (OTP, Twilio, checkout) | BUILT |
| MCP delivery mode | BUILT |
| Overseer admin SPA | BUILT (dashboard, entities, approvals) |
| ChromaDB RAG | BUILT |
| Klikk bridge | BUILT |
| Classification engine | PARTIAL (Smart ID only) |
| POPIA DSAR self-service | NOT STARTED |
| Production deployment | NOT STARTED |
| pytest suite + CI | NOT STARTED |
| Key rotation / HSM | NOT STARTED |

**Live data:** 1 vault owner (mc@tremly.com), 90 entities (78 personal, 12 assets), 0 documents, 0 relationships.

---

## Key Technical Details

- **Repo:** `/Users/mcdippenaar/PycharmProjects/vault33/`
- **Backend:** Django 5 + DRF, PostgreSQL, `:8001`
- **Frontend:** Vue 3 Overseer SPA (Pip-Boy CRT styling), `:5174`
- **MCP:** FastMCP stdio + streamable HTTP (`:8765`)
- **Admin login:** `admin` / `admin`
- **API keys:** `volt_owner_` prefix (SHA-256 hashed, raw shown once)
