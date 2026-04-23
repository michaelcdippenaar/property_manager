# Vault33 — Statement of Work

> **Version:** 1.0 · **Date:** 2026-04-17 · **Author:** MC Dippenaar / Claude  
> **Status:** Draft — scoping  
> **Companion:** `docs/system/vault33-system-document.md`

---

## 1. Objective

Bring Vault33 from its current **working prototype** (models + MCP + REST built, no data populated, no frontend, no production deployment) to a **production-grade personal data vault** that:

1. Stores and secures all FICA, POPIA, and RHA-required data for every entity in the Klikk ecosystem
2. Serves as the single source of truth for the Klikk data flow (as defined at `localhost:8006/data`)
3. Enables AI-assisted document classification, entity resolution, and BO chain analysis via MCP
4. Provides self-service data-subject rights for tenants (POPIA §23/§24)
5. Enables consent-gated data sharing with external parties (conveyancers, banks, agents)

---

## 2. Current State Assessment

### What's built

| Component | Maturity | Confidence |
|-----------|----------|------------|
| Django models (15+ models) | Production-ready | High |
| REST API (20+ endpoints) | Production-ready | High |
| MCP server (23 tools, 2 transports) | Production-ready — recent +1,247-line expansion **staged, uncommitted** | High |
| Fernet encryption (per-owner) | Production-ready | High |
| Append-only audit log | Production-ready | High |
| Document type catalogue (~85 types) | Seeded via migration (**uncommitted 0005**) | High |
| Relationship type catalogue (10 types) | Seeded via migration (**uncommitted 0007**) | High |
| Entity schemas (ZA defaults) | Production-ready | High |
| Gateway consent flow | Functional prototype | Medium |
| Classification entity engine | **Full pipeline built** (entity_engine, document_provenance, router, prompts) — **uncommitted** | Medium |
| Extraction skills | **5 SA ID skills built**: Smart ID, Passport, Driver's Licence, Green ID Book, Unabridged Birth Cert — **uncommitted** | Medium |
| Ingestion pipeline (manifest → enrich → upload) | **Built and run** — 741 MB / 496 `.enc` files on disk — **uncommitted** | Medium |
| ChromaDB vector indexing | Basic (auto-index on upload) | Low |
| Test coverage | **Zero** test files in `apps/the_volt/` (17,974 LoC) | — |

### What's missing

| Gap | Impact | Effort |
|-----|--------|--------|
| **Commit + inventory of local work** | ~1,247 staged lines + 35 untracked files + 6 untracked migrations + 741 MB of ingested data; no visibility on what's in DB vs. on disk | Small (sprint) |
| **DB / filesystem reconciliation** | 496 on-disk `.enc` files — how many are orphaned? | Small |
| **Zero test coverage** | 17,974 LoC with no automated verification | Medium |
| No admin SPA frontend | Cannot manage vault visually | Large |
| No tenant-facing data rights UI | POPIA non-compliance | Medium |
| Ingestion queue not fully drained | 1,082 manifest entries, 15 enriched batches; completion unknown | Medium |
| No production deployment | Local-only, single-owner | Medium |
| No key rotation / HSM | Security gap | Medium |
| No email ingestion pipeline | File-based manifest ingestion works; email-triggered ingestion missing | Medium |
| No CIPC / SARS API integration | Manual data entry / OCR only | Medium |
| Proof-of-address classifier | Utility bills, bank statements — not yet a dedicated skill | Small |
| No alerting / monitoring | No anomaly detection on access patterns | Small |
| No data retention automation | Manual tracking of expiry dates | Medium |
| Per-recipient document watermarking | Cannot trace leaked docs to specific recipient | Medium |
| Container-based delivery (encrypted PDF / `.klikk` / streaming viewer) | Checkout packages are plain PDFs with no access control post-delivery | Medium-Large |

---

## 3. Phases

### Phase 0 — Foundation Clean-up & Inventory (Week 1)

**Goal:** Commit the substantial local work, reconcile DB vs. filesystem, fix structural issues, establish test baseline.

| # | Deliverable | Detail | Effort |
|---|------------|--------|--------|
| 0.1 | **Commit sprint** — MCP tool expansion | Commit the 9 staged files (+1,247 lines, mostly `mcp/tools/read.py` & `write.py`) with proper message + review | 2h |
| 0.2 | **Commit sprint** — migrations + seeds | Commit migrations 0005–0009 (document catalogue seed, relationship catalogue + seed, asset docs seed, company/trust/CC/soleprop seeds) | 1h |
| 0.3 | **Commit sprint** — classification pipeline | Commit untracked `classification/` module (35 files), `mcp/upload_from_manifest.py`, `mcp/UPLOAD_PIPELINE.md`, `mcp/manifests/`, `docs/architecture-diagram.md` | 2h |
| 0.4 | **Push to origin/main** | Publish the 1-commit-ahead branch + new commits | 0.5h |
| 0.5 | DB / filesystem reconciliation | Reconcile `DocumentVersion.count()` vs. `ls media/vault \| wc -l` (current: 496 `.enc` files, 741 MB); garbage-collect orphaned ciphertext | 4h |
| 0.6 | Ingestion queue audit | Reconcile 1,082 manifest entries + 15 enriched batches against DB state; identify what's uploaded vs. pending vs. failed | 4h |
| 0.7 | Test baseline | Create `apps/the_volt/tests/` with skeleton `test_encryption.py`, `test_entities_upsert.py`, `test_mcp_tools.py`, `test_gateway_checkout.py`; enforce CI on new PRs | 2d |
| 0.8 | Vault data reset (if required post-reconcile) | Wipe orphaned/duplicate entities (e.g. the 3 duplicate "MC Dippenaar" records, typo entity #89) | 2h |
| 0.9 | Entity deduplication rules | Define merge strategy for duplicate personal entities (e.g. "Tanja" vs "Tanja Naudé", "Matthew" vs "Matthew van Helsdingen") | 4h |
| 0.10 | Relationship type expansion | Add missing types: `spouse_of`, `child_of`, `employed_by`, `attorney_for`, `auditor_of`, `beneficiary_of` (trust) | 2h |
| 0.11 | Document type audit | Verify all 85 catalogue entries have correct extraction schemas, issuing authorities, validity periods | 4h |
| 0.12 | MCP tool hardening | Add input validation, error messages, rate limiting to MCP write tools | 4h |

**Exit criteria:** All local work committed and pushed. DB state reconciled against filesystem. Test infrastructure in place. Catalogue fully validated. **This phase expands from 1 week to ~1.5 weeks given the unexpected inventory work.**

**Exit criteria:** Clean vault, validated catalogues, hardened MCP tools.

---

### Phase 1 — Data Population (Weeks 2–4)

**Goal:** Populate the vault with real entity data, documents, and relationships for the MC Dippenaar portfolio.

#### 1A — Core entities

| # | Deliverable | Detail | Effort |
|---|------------|--------|--------|
| 1.1 | Owner entity (MC Dippenaar) | Full personal data: ID, DOB, address, tax, marital status, spouse | 1h |
| 1.2 | Family entities | Tanja Naudé, Lia Dippenaar, Stefanie Dippenaar, Luca Naude, MC Jnr, Michael Snr | 2h |
| 1.3 | Company entities | LucaNaude (Pty) Ltd, Klikk (Pty) Ltd, Tremly (Pty) Ltd | 2h |
| 1.4 | Trust entities | Naude Dippenaar Trust IT001973/2025, MLD Trust (if applicable) | 2h |
| 1.5 | Asset entities (properties) | All 14 properties with ERF numbers, title deed refs, addresses, values | 4h |

#### 1B — Relationship graph

| # | Deliverable | Detail | Effort |
|---|------------|--------|--------|
| 1.6 | Direct relationships | MC → director_of → companies; MC → trustee_of → trusts; MC → parent_of → children | 2h |
| 1.7 | Ownership chains | Trust → shareholder_of → LucaNaude (share_pct, effective_date); Companies → holds_asset → properties | 2h |
| 1.8 | Tenant relationships | All current tenants → leases_from → their respective properties | 4h |
| 1.9 | BO chain validation | Verify multi-hop BO resolution: MC → Trust → Company → Asset | 2h |

#### 1C — Document ingestion (drain the existing queue)

> **Correction:** the ingestion pipeline is already built (`mcp/upload_from_manifest.py`) and partially run (741 MB / 496 `.enc` files already encrypted to disk). This phase **completes the ingestion** rather than starting it.

| # | Deliverable | Detail | Effort |
|---|------------|--------|--------|
| 1.10 | Drain `klikk_manifest` (130 entries) — 5 enriched batches already built | Run upload stage, verify entity/document/relationship creation | 4h |
| 1.11 | Drain `tremly_manifest` (704 entries) — largest cluster | Break into batches, OCR-enrich the unprocessed entries, run upload stage | 2d |
| 1.12 | Drain `lucanaud_manifest` (49) + `mld_trust_manifest` (49) | Including trust deed, Letters of Authority, directors | 1d |
| 1.13 | Drain `mc_dippenaar_jnr_manifest` (78) + `mc_dippenaar_testamentere_trust` (25) + `michael_dippenaar_snr` (12) + `koniba_belegings` (10) + `stefanie` (10) + `lia_dippenaar` (5) + `mc_dippenaar_boerderye` (7) + `naude_dippenaar_trust` (2) + `joyle/luca/tanja` (0–1 each) | Remaining family / ancillary entity manifests | 1.5d |
| 1.14 | Post-ingestion audit | For every entity, verify required FICA docs are attached; flag gaps | 4h |
| 1.15 | Tenant FICA top-up | ID + Proof of Address for each active tenant not yet covered by manifest | 1d |

**Exit criteria:** Complete entity graph for all 16 entity clusters. All entities have FICA-grade documentation attached. BO chains resolve correctly via multi-hop traversal. **Phase 1 realistic duration: 2 weeks (was 3).**

---

### Phase 2 — Classification & Extraction (Weeks 4–6)

> **Correction:** the classification pipeline is already built — 5 SA ID extraction skills, entity_engine, document_provenance, router, consensus_extract all exist on disk (uncommitted). This phase **hardens, tests, and extends** the existing pipeline rather than building it from scratch.

**Goal:** Stabilise the existing pipeline, add missing classifiers, wire up readiness dashboard, automate email-triggered ingestion.

| # | Deliverable | Detail | Effort |
|---|------------|--------|--------|
| 2.1 | **Harden existing 5 ID skills** | Add unit tests, edge cases (damaged IDs, rotated images, low-quality scans); verify all extract correctly against a test corpus | 3d |
| 2.2 | Proof of Address classifier | Utility bill / bank statement / lease-as-proof detection + address extraction (not yet built) | 2d |
| 2.3 | CIPC document classifier hardening | Verify routing of CoR14.x, CoR15.x, CoR21.x, CoR39, share certs; tighten extraction schemas from already-enriched manifests (they have this data structurally correct) | 2d |
| 2.4 | Trust document classifier | Trust deed + Letters of Authority parsing | 2d |
| 2.5 | Property doc classifiers | OTP, bond_statement, title deed, rates clearance, electrical/gas/beetle COCs, rental agreement — all have worked examples in `klikk_batch2` and `klikk_batch3a` enriched manifests | 3d |
| 2.6 | Multi-document consensus | Formalise existing `consensus_extract.py` into tested, repeatable cross-validation of extracted fields across documents | 2d |
| 2.7 | Inbound email pipeline | Monitor inbox → attachment → manifest auto-generation → enrich → upload (new work) | 5d |
| 2.8 | Readiness dashboard data | Slot engine integration — compute FICA readiness per entity type (slot engine built; wiring to API not yet) | 2d |
| 2.9 | ChromaDB hybrid search | Wire existing `vectorisation_rules.py` into `VaultQueryService.traverse()` for hybrid graph+vector queries | 3d |

**Exit criteria:** Upload any supported SA document → system classifies it, extracts structured data, links to correct entity, updates field provenance, recomputes readiness. Email-triggered ingestion end-to-end. **Phase 2 realistic duration: 3 weeks (was 4).**

---

### Phase 3 — Admin Frontend (Weeks 9–12)

**Goal:** Vue 3 admin SPA pages for vault management — visual entity graph, document viewer, readiness dashboard.

| # | Deliverable | Detail | Effort |
|---|------------|--------|--------|
| 3.1 | Entity list page | Filterable/searchable list of all vault entities by type | 3d |
| 3.2 | Entity detail page | Full entity record: data fields, documents, relationships, provenance trail | 5d |
| 3.3 | Relationship graph visualisation | Interactive D3/Cytoscape graph showing BO chains and entity connections | 5d |
| 3.4 | Document viewer | In-browser document preview with version history, verification status | 3d |
| 3.5 | Document upload flow | Drag-drop upload → classification → entity linking → extraction preview | 3d |
| 3.6 | Readiness dashboard | Per-entity FICA compliance score, missing documents, expiring proofs | 3d |
| 3.7 | Gateway request management | List incoming data requests, approve/deny with OTP, view checkout history | 3d |
| 3.8 | Audit log viewer | Searchable, filterable view of VaultWriteAudit records | 2d |
| 3.9 | BO Register generator | One-click generation of beneficial_ownership_register.json per company entity | 2d |

**Exit criteria:** Agent/owner can manage all vault operations through the admin SPA without touching MCP or Django admin.

---

### Phase 4 — Tenant Data Rights (Weeks 13–14)

**Goal:** POPIA §23/§24 self-service in the tenant mobile app and web app.

| # | Deliverable | Detail | Effort |
|---|------------|--------|--------|
| 4.1 | "My Data" screen | Tenant sees what PI Klikk holds about them (entity + documents) | 3d |
| 4.2 | Data access request (DSAR) | Tenant requests a downloadable copy of all their PI; auto-packages from vault | 3d |
| 4.3 | Correction request | Tenant flags inaccurate data → creates support ticket + vault annotation | 2d |
| 4.4 | Deletion request | Tenant requests account deletion → system checks FICA/RHA retention holds → schedules or explains delay | 2d |
| 4.5 | Marketing opt-out | Immediate unsubscribe from all marketing communications | 1d |
| 4.6 | Audit trail for data subject | Tenant can see who accessed their data (via DataCheckout records) | 1d |

**Exit criteria:** Tenant can exercise all POPIA rights through the app. 30-day SLA tracked. FICA/RHA retention holds enforced automatically.

---

### Phase 5 — Production Hardening + Delivery Security (Weeks 13–15)

**Goal:** Production-ready deployment with proper security, monitoring, operational controls, and **forensic-grade per-recipient document delivery**.

#### 5A — Infrastructure & compliance

| # | Deliverable | Detail | Effort |
|---|------------|--------|--------|
| 5.1 | Key rotation mechanism | Rotate Fernet keys without re-encrypting all documents (envelope encryption) | 3d |
| 5.2 | AWS KMS integration | Replace PBKDF2 key derivation with KMS-managed keys | 2d |
| 5.3 | S3 encrypted storage | Move document files from local filesystem to S3 af-south-1 with KMS encryption | 2d |
| 5.4 | Rate limiting | MCP tool rate limits, REST API throttling | 1d |
| 5.5 | Monitoring & alerting | Anomalous access pattern detection, failed auth alerts, document access logging | 2d |
| 5.6 | Backup & recovery | Automated DB backups, document recovery procedure, disaster recovery plan | 2d |
| 5.7 | Data retention automation | Auto-flag expired documents, schedule purge after retention period, FICA hold enforcement | 2d |
| 5.8 | Penetration testing | Security audit of gateway, MCP, REST API | 2d |
| 5.9 | POPIA compliance audit | End-to-end verification against Information Regulator checklist | 1d |

#### 5B — Per-recipient document watermarking (leak attribution)

| # | Deliverable | Detail | Effort |
|---|------------|--------|--------|
| 5.10 | PDF metadata watermark | Subscriber ID + checkout token in `/Info` + XMP | 1d |
| 5.11 | Invisible visual watermark | White-on-white footer + zero-width unicode markers per recipient | 2d |
| 5.12 | Forensic fingerprint | Per-recipient micro-perturbations (kerning, spacing, JPEG quantization) + `CheckoutWatermark` registry | 5d |
| 5.13 | Watermark extraction tool | Given a leaked PDF, match back to checkout → subscriber | 2d |
| 5.14 | Non-PDF handling | Images: LSB watermarking. DOCX: metadata + style variation. Raw-data exports (JSON/CSV): require DPA in lieu of watermark | 2d |

#### 5C — Container-based delivery modes

| # | Deliverable | Detail | Effort |
|---|------------|--------|--------|
| 5.15 | `delivery_mode` field on `DocumentTypeCatalogue` | Classify all 85 doc types: PLAIN / ENCRYPTED / CONTAINER / STREAMING | 2d |
| 5.16 | Encrypted PDF packager (Option 1) | Per-checkout password, delivered via split channel (SMS) | 2d |
| 5.17 | `.klikk` container format + Vault Viewer (Option 2) | Wrapper format with manifest + signature; Electron/browser viewer with permit callback | 10d |
| 5.18 | Streaming viewer (Option 3) | Server-side PDF rasterisation; paginated image delivery with per-page audit + dynamic watermark | 10d |
| 5.19 | Permit callback + revocation API | Every viewer session calls home → Vault33 returns yes/no + decryption key; revocation is instant | 3d |

**Exit criteria:** Production deployment on AWS af-south-1. KMS-managed keys. Automated backups. Monitoring active. Pen test clean. **Every outbound document carries a per-recipient watermark; high-sensitivity docs never leave the server (streaming viewer) or are delivered in `.klikk` containers with revocable access.**

---

### Phase 6 — External Integrations (Weeks 17–20)

**Goal:** Connect to external data sources and consumers to reduce manual data entry and enable automated compliance.

| # | Deliverable | Detail | Effort |
|---|------------|--------|--------|
| 6.1 | CIPC API integration | Auto-lookup company registration data, directors, shareholders | 5d |
| 6.2 | SARS eFiling integration | Tax number verification, tax clearance status | 3d |
| 6.3 | TransUnion / Compuscan | Credit check results stored as documents on tenant entities | 3d |
| 6.4 | DHA verification | ID number validation against Home Affairs (where API available) | 2d |
| 6.5 | Banking partner integration | Trust account balance feeds, deposit interest calculations | 5d |
| 6.6 | Conveyancer portal | Dedicated STBB/conveyancer login for gateway access (replaces manual OTP per-request) | 5d |
| 6.7 | Accountant / auditor portal | Read-only access to financial documents for annual audit | 3d |

**Exit criteria:** Key external parties can request and receive data electronically. Manual document collection reduced by >70%.

---

## 4. Dependencies

| Dependency | Blocks | Status |
|-----------|--------|--------|
| Django backend running | All phases | ✅ Running |
| PostgreSQL | All phases | ✅ Running |
| ChromaDB | Phases 2, 3 | ✅ Running (local) |
| AWS account (af-south-1) | Phase 5 | ⚠️ Needs provisioning |
| AWS KMS | Phase 5 | ⚠️ Needs provisioning |
| CIPC API access | Phase 6 | ❌ Needs application |
| TransUnion API access | Phase 6 | ❌ Needs application |
| DHA API access | Phase 6 | ❌ Needs application (limited availability) |
| STBB/conveyancer agreement | Phase 6 | ❌ Needs negotiation |
| Source documents (ID, title deeds, CIPC docs) | Phase 1 | ✅ Available in Downloads |
| Trust deed + Letters of Authority | Phase 1 | ⚠️ Need to locate |

---

## 5. Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|-----------|
| FICA retention conflicts with POPIA deletion | Data subject requests deletion but FICA requires 5-year hold | High | Automated hold logic (Phase 4.4); clear tenant communication |
| SECRET_KEY compromise = all vault data exposed | Catastrophic — all documents decryptable | Medium | Move to KMS (Phase 5.2); envelope encryption (Phase 5.1) |
| ChromaDB scalability (local SQLite) | Vector search degrades with >100K documents | Low (short term) | Migrate to hosted Chroma or Pinecone at scale |
| CIPC API reliability | Company data lookups fail or are slow | Medium | Cache results in vault entities; manual fallback |
| Extraction skill accuracy | Incorrect OCR leads to wrong data in entity fields | Medium | Multi-model consensus (Phase 2.8); manual review flag |
| Gateway package interception | Checkout data readable in transit | Low | TLS required; future: end-to-end encryption |
| Scope creep from additional entity types | New business structures (partnerships, co-ops) need modelling | Medium | Schema-driven design handles this without migrations |

---

## 6. Success Criteria

### Phase 1 (MVP)
- [ ] All MC Dippenaar portfolio entities exist with correct data
- [ ] BO chain resolves correctly: MC → Trust → Company → Asset
- [ ] FICA documents attached to all key entities
- [ ] MCP tools return correct, complete data for any entity query

### Phase 2
- [ ] Upload any SA identity document → auto-classified, extracted, linked within 30 seconds
- [ ] FICA readiness score computable for any entity
- [ ] Cross-document consensus catches contradictions (e.g. ID says DOB X, passport says DOB Y)

### Phase 3
- [ ] Agent can manage entities, documents, relationships entirely through admin SPA
- [ ] BO graph renders correctly for multi-hop chains
- [ ] One-click BO Register generation produces valid JSON per schema

### Phase 4
- [ ] Tenant can request DSAR and receive data package within 30 days (automated)
- [ ] FICA/RHA holds block premature deletion with clear explanation to tenant
- [ ] Marketing opt-out takes effect within 1 business day

### Phase 5
- [ ] All documents encrypted with KMS-managed keys on S3 af-south-1
- [ ] Zero downtime key rotation
- [ ] Pen test produces no critical/high findings
- [ ] POPIA compliance audit passes

### Phase 6
- [ ] CIPC lookups populate company entities automatically
- [ ] Conveyancers access FICA packs via portal (no manual email)
- [ ] Manual document collection reduced by >70% vs. current workflow

---

## 7. Estimated Timeline (revised after 2026-04-17 audit)

| Phase | Duration | Start | End | Notes |
|-------|----------|-------|-----|-------|
| Phase 0 — Foundation + Inventory | 1.5 weeks | Week 1 | mid-Week 2 | Expanded — commit sprint + DB/FS reconcile + test baseline |
| Phase 1 — Data Population | 2 weeks | Week 2 | Week 3 | Reduced — ingestion pipeline already built, ~1,082 manifest entries to drain |
| Phase 2 — Classification | 3 weeks | Week 4 | Week 6 | Reduced — 5 ID skills already built; hardening + email pipeline |
| Phase 3 — Admin Frontend | 4 weeks | Week 7 | Week 10 | Unchanged |
| Phase 4 — Tenant Rights | 2 weeks | Week 11 | Week 12 | Unchanged |
| Phase 5 — Production + Delivery Security | 3 weeks | Week 13 | Week 15 | Expanded — adds watermarking + container delivery (see §5.10–5.19) |
| Phase 6 — Integrations | 4 weeks | Week 16 | Week 19 | Unchanged |

**Total: ~19 weeks (~4.5 months)** — net reduction of 1 week vs. original scope, because Phases 1 and 2 are materially further along than first believed, offsetting the Phase 0 expansion and Phase 5 additions.

Phases 2 and 3 can overlap if frontend work starts with mock data while classification skills are being hardened.

---

## 8. Out of Scope

The following are explicitly **not** in this SOW:

- Klikk Rentals product features (leases, tenant management, maintenance) — those exist separately
- Klikk Real Estate product (sales/OTP management) — separate product line
- Klikk BI product (analytics/reporting) — separate product line
- Marketing website — separate workstream
- Mobile app redesign — separate workstream
- Multi-tenant SaaS deployment (Vault33 is single-owner per instance; SaaS would need tenant isolation, billing, onboarding — a separate project)

---

## 9. Glossary

| Term | Definition |
|------|-----------|
| **BO** | Beneficial Owner — natural person who ultimately owns or controls an entity (Companies Act §56(7)) |
| **CDD** | Customer Due Diligence — FICA §21 KYC requirements |
| **DSAR** | Data Subject Access Request — POPIA §23 right to access |
| **FICA** | Financial Intelligence Centre Act 38/2001 |
| **Gateway** | Vault33's external data sharing mechanism with consent flow |
| **MCP** | Model Context Protocol — Anthropic's protocol for AI tool integration |
| **OTP** | One-Time Password — used for gateway consent |
| **PI** | Personal Information (POPIA definition) |
| **POPIA** | Protection of Personal Information Act 4/2013 |
| **RHA** | Rental Housing Act 50/1999 |
| **Slot** | A required data field or document for an entity type |
| **VCN** | Vault Classification Number — unique document identifier |
| **Vault** | A single-owner data store within Vault33 |
