---
name: klikk-documents-owner-cipro
description: >
  SA owner/landlord document intake, CIPRO/CIPC classification, FICA compliance,
  and scenario-specific readiness (rental mandate signing, property purchase).
  ALWAYS use this skill when a landlord/owner/entity is being onboarded, verified,
  classified, or needs to have their documents parsed — even if the user doesn't
  explicitly say "classify". Triggers on: "add owner", "onboard landlord",
  "verify owner", "classify owner documents", "CIPC document", "CIPRO documents",
  "CoR14.3", "CoR39", "CK1 document", "CK2", "registration certificate",
  "trust deed", "Letters of Authority", "FICA company documents", "beneficial
  ownership", "director extraction", "landlord documents", "SA company docs",
  "rental mandate", "mandate signing", "who can sign", "owner FICA",
  "proof of address check", "bank confirmation letter", "SARS tax number".
  Use this skill whenever a folder of owner documents is mentioned or dropped,
  whenever a user asks what's missing for a rental mandate, or whenever
  entity/director/trustee information needs to be extracted from uploaded files.
---

# SA Owner Document Classifier (CIPRO · FICA · Persons Graph · Mandate Readiness)

AI compliance agent for South African owner/landlord document intake. Classifies uploaded files into FICA and CIPC/CIPRO buckets, extracts structured fields, builds a beneficial-ownership persons graph, computes scenario-specific readiness (rental mandate today; property purchase planned), and writes `owner_classification.json`.

---

## Scenario selector

Callers pass a scenario so the skill knows which readiness block to compute:

| Scenario | Use | Reference file |
|----------|-----|----------------|
| `rental_mandate` | Owner → managing agent mandate | [mandate-requirements.md](references/mandate-requirements.md) |
| `purchase` *(planned, v2)* | Owner buying a property | *(not yet authored)* |

If no scenario is provided, default to `rental_mandate` — it's the dominant flow.

---

## Pipeline Summary

| Phase | Action |
|-------|--------|
| 1 | Declare entity type (Individual / Company / Trust [*inter vivos* or *testamentary*] / CC / Partnership). For trusts, distinguish on the founding document: Trust Deed = inter vivos; Last Will and Testament = testamentary. |
| 2 | Ingest all files from folder (Glob + Read) |
| 3 | Classify each document into FICA or CIPC bucket |
| 4 | Extract structured fields per document |
| 5 | Validate completeness against entity requirements |
| 6 | Write `owner_classification.json` |
| 7 | Build cross-entity persons graph + system lookup |
| 8 | *(server-side)* Chunk + embed documents into ChromaDB `owner_documents` |
| 9 | *(server-side)* Compute scenario-specific gap analysis |

Phases 1–7 are what the skill executes directly. Phases 8–9 are the backend integration points — the skill's job there is to *produce output shaped for them*, not run them itself. Read the relevant reference file only when you reach that phase; don't pre-load all of them.

---

## Reference Index

| Topic | When to load |
|-------|--------------|
| Full pipeline protocol (Phases 1–9), classification signals, extraction rules, persons graph, system lookup | [pipeline.md](references/pipeline.md) — load at Phase 1 |
| Complete CIPC/CIPRO document taxonomy + extraction fields per form | [cipc-document-taxonomy.md](references/cipc-document-taxonomy.md) — load at Phase 4 when extracting CIPC docs |
| FICA requirements per entity type (required / optional docs) | [fica-requirements.md](references/fica-requirements.md) — load at Phase 5 |
| Output JSON structure — base, trust_entity, persons_graph, readiness schemas | [output-schema.md](references/output-schema.md) — load at Phase 6 |
| **Rental mandate requirements** — who can sign, required fields, bank/title deed rules | [mandate-requirements.md](references/mandate-requirements.md) — load at Phase 9 when scenario=`rental_mandate` |
| RAG ingestion spec (ChromaDB collection, chunking, metadata schema) | [rag-ingestion.md](references/rag-ingestion.md) — load when implementing or debugging Phase 8 |
| AI chat playbook (tone, proactive greeting, tool-use patterns, question prioritisation) | [chat-playbook.md](references/chat-playbook.md) — load when working on the owner chat endpoint/UI |

---

## Two entry points

1. **Full classify** — `POST /api/v1/properties/landlords/{pk}/classify/`
   Reads all `LandlordDocument` files + `registration_document`, runs the full Phases 1–7 pipeline.

2. **Registration-only classify** — `POST /api/v1/properties/landlords/{pk}/classify-registration/`
   Processes a single registration document (CIPC cert, trust deed, or ID) and patches entity fields quickly. Useful during fast onboarding.

Both endpoints live in `backend/apps/properties/classify_view.py` and store output in `Landlord.classification_data` (JSONField).

---

## Key Rules

- **Never infer or guess field values** — extract only what is explicitly present in the document
- **Bank accounts**: last 4 digits only — never log the full number
- **SA ID format**: 13 digits; validate format, do not compute checksum
- **Registration numbers**: `YYYY/XXXXXX/07` format (07=Pty Ltd, 08=CC, 21=NPC, 06=Public Ltd)
- **Trust numbers**: `ITxxxx/yyyy` format (Master of the High Court URN)
- **Dates**: always normalise to `YYYY-MM-DD`
- **Persons graph**: deduplicate by ID number across all entities; flag control concentration
- **FICA reuse**: one certified ID per person covers all their roles in this folder
- **Letters of Authority currency**: If Letters of Authority don't list the trustees currently claiming authority, flag as a **blocking issue** for rental mandate — a stale LoA means no one listed on it can sign

## Why this matters

A rental mandate is a legal grant of authority from an owner to a managing agent. If the wrong person signs — a director who isn't authorised under the MOI, a trustee whose Letters of Authority have been superseded — the mandate is voidable. That's what Phase 9 (gap analysis) exists to prevent: surfacing the blocking issues *before* the signature request goes out, not after the first rent payment bounces.
