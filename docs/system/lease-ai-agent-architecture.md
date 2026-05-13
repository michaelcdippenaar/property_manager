# Klikk Lease AI — Multi-Agent Architecture

| Field | Value |
|---|---|
| **Status** | Design locked (post-audit refactor), ready to build |
| **Phase** | 0 → 0.5 (prerequisites) → 1 |
| **Date locked** | 2026-05-12 (initial); 2026-05-12 (post-audit revision); 2026-05-12 (citation-map cutover) |
| **Author** | MC + Claude (design conversation); pre-implementation audit by CTO agent on Opus; second audit grounded in SA law (citation findings consolidated in `content/cto/rha-citation-canonical-map.md`) |
| **Implementation target** | `apps.leases.template_views` + new `apps.leases.lease_law_corpus/` + new `apps.leases.runner.LeaseAgentRunner` |
| **Endpoint** | `POST /api/v1/leases/templates/<id>/ai-chat-v2/` (parallel to v1 until cutover) |
| **Supersedes** | Single-agent `LeaseTemplateAIChatView` (kept as fallback during rollout) |
| **Audit findings applied** | 6 P0 (caching, forced tool output, loop math, coordinator class, indexing race, case-law verifier), 2 P1 (push viability, runtime — re-scoped from "migrate to ASGI" to "production is daphne; one Caddy `flush_interval -1` handler + `async def` view" per `docs/system/lease-ai-asgi-decision.md`), 5 risk-register items. Citation-map cutover applied HIGH-confidence corrections (RHT establishment s13→s7; POPIA accuracy s23→s16); LOW-confidence sub-section letters remain provisional pending SA-admitted-attorney sign-off — see `content/cto/rha-citation-canonical-map.md`. |

---

## 1. TL;DR

A cluster of cooperating Claude agents, backed by a versioned SA-rental-law RAG, that:

- **Generates** SA-compliant residential lease agreements from a brief, with merge fields baked in
- **Formats** them for publication — running header, no orphan content at page boundaries, per-page initials placeholder, readable type
- **Audits** existing leases against statute, and (optionally on request) against Rental Housing Tribunal case law + pitfall patterns
- **Inserts** targeted clauses on user request without rewriting the whole document
- **Understands context** — sectional title vs freehold vs commercial, tenant count, lease type, special conditions

The architecture is **three specialist agents** (Drafter, Reviewer, Formatter) coordinated by a **Front Door** that builds context and dispatches. A **RAG store** is the single source of truth for SA rental law — Drafter assembles from it, Reviewer audits against it. The pipeline gates on the Reviewer (which can send work back to the Drafter for revision, max 1 retry). The user sees one coherent reply.

The RAG ships as ChromaDB-in-app for v1, with the corpus as portable YAML; v2 carves it out as a standalone MCP server (potentially a product).

---

## 2. Why this — failure modes the current single-agent has

Before designing the system, the failures we're solving:

1. **AI confidently describes work it didn't do.** Claude says "I've added 13 sections to your lease" while emitting 13 `[needs completion]` placeholders. The model is asked to draft AND quality-control in one head; quality control loses.
2. **AI assembles from "what's available" without checking applicability.** Claude pulls `tenant_2_*` / `tenant_3_*` merge fields because they're advertised, even when the user has one tenant. **Resolved 2026-05-13:** merge-fields catalogue migrated to `content/legal/merge_fields/` YAML with per-field `applicability.tenant_counts`. Front Door's `merge_fields_loader.filter_by_context()` returns only applicable fields; Drafter never sees `tenant_2_*` for a 1-tenant request. See `backend/apps/leases/merge_fields_loader.py` + `content/legal/merge_fields/`.
3. **AI handcrafts content where a curated library would be better.** Lease clauses are well-established law — the model regenerating them every time introduces variability the law doesn't have.
4. **AI has no awareness of formatting concerns.** Same Claude reasons about clause content AND heading hierarchy AND page breaks; can't do all three well.
5. **AI's legal knowledge is whatever was in training, not what's current.** No way to update it; no audit trail of "what law was the AI working from when it generated this lease".

Multi-agent + RAG fixes all five.

---

## 3. Goals and non-goals

### In scope (v1)

- SA residential leases (sectional title + freehold + apartment + townhouse)
- Generate, edit, audit, format, targeted clause insertion, conversational Q&A about SA rental law
- Klikk-uniform layout (single house style)
- English only
- Statute-grounded audit (RHA, CPA, POPIA, PIE Act, Sectional Titles Schemes Management Act)
- Opt-in case-law audit (against curated RHT decisions + pitfall patterns)

### Out of scope (deferred)

- Commercial leases (different statute set)
- Sales OTPs, mandates, supplier contracts (Phase 5+ — same architecture, different drafter)
- Multi-language (Afrikaans, IsiZulu — future)
- Per-agency layout customisation (Tier D)
- Real-time legal-knowledge feed (quarterly + event-driven for v1)
- Lawyer-on-call review path (the corpus is `ai_curated` / `mc_reviewed`; lawyer-blessed comes before external customer launch)

---

## 4. Locked architectural decisions

| # | Decision | Choice |
|---|---|---|
| 1 | Number of agents | **3 specialists + 1 front-door (Python, not LLM)** |
| 2 | Reviewer role | **Gate** — can veto, sends back to Drafter |
| 3 | Single source of legal truth | **RAG store** (ChromaDB-in-app v1, MCP product v2) |
| 4 | Corpus tier | **Tier C** — clauses + statutes + 30-50 case law + ~50 pitfall patterns |
| 5 | Corpus storage | **ChromaDB-in-app for v1**, **standalone MCP server for v2** |
| 6 | Corpus canonical form | **YAML files in `backend/apps/leases/lease_law_corpus/`**, indexed by `manage.py reindex_lease_corpus` (NOT on startup — see §6.3) |
| 7 | Corpus maintenance | **Code-only YAML + git PR** for v1; admin-UI deferred to Tier D |
| 8 | Indexing strategy | **Tags + citations + semantic** (all three on same chunks) |
| 9 | Query pattern | **Push for Drafter** (Front Door inlines clauses), **pull for Reviewer** (tool calls on demand). Push viability is **conditional on prompt caching working** — see decision 18. |
| 10 | Reviewer loop budget | **1 retry max.** Hard caps enforced in `LeaseAgentRunner` coordinator: **≤8 total LLM calls per request**, **≤90s wall-clock budget**, **≤3 internal turns per agent**. On cap-hit: ship partial result with `terminated_reason=cap` and a banner to the user. Realistic worst case is 6-8 calls, not 4 — see §8.1 for the honest math. |
| 11 | Tool partitioning | **Strict** — each agent gets only tools matching its role. Enforced per-call (each `messages.create` defines its own tools list). |
| 12 | Question-asking UX | **Conversational** — agent asks in plain text, user answers in next message |
| 13 | Case-law sourcing | **AI-curated seed (Claude + MC review) → canonical-map drift check → MC review → staging/internal use → SA-lawyer attestation before external customer.** No `case_law` chunk advances past `confidence_level=ai_curated` until `manage.py verify_caselaw_citations` confirms (a) every statute citation in the chunk matches the canonical map, AND (b) the chunk carries a lawyer-attested `verification_status: verified` field. SAFLII fetching is Cloudflare-blocked, so we cannot programmatically verify case-law URLs at runtime — lawyer attestation is the substitute. See decision 19 + §6.5. |
| 14 | Page layout | **Klikk-uniform for v1** — per-agency customisation deferred to Tier D |
| 15 | UX disclosure | **One coherent reply, pipeline visible in tools-used badges** — audit report in expander. Every Reviewer finding shows its `confidence_level` (ai_curated / mc_reviewed / lawyer_reviewed) so the user knows the strength of the citation. |
| 16 | API contract | **`POST /api/v1/leases/templates/<id>/ai-chat-v2/`** alongside v1 during rollout; v1 retired after stability |
| 17 | Streaming | **SSE within v2 from day one** — token streaming inside turns, status events between agents. Production runtime is already daphne ASGI (`backend/Dockerfile:27`); the v2 view is `async def` and the lease-AI Caddy block sets `flush_interval -1`. Per ADR `docs/system/lease-ai-asgi-decision.md`. See §10.2. |
| **18** | **Prompt caching (mandatory)** | **`cache_control: {"type": "ephemeral"}` markers on tools array + 3 system-prompt blocks (persona, merge-fields block, RAG chunks block).** Per-request user data lives AFTER the last breakpoint. Audit telemetry: every Drafter call after the first in a session MUST report `cache_read_input_tokens > 0` — failure raises a sev-2 alert. See decision 22 + §6.6. |
| **19** | **Citation verifier CLI** | **`manage.py verify_caselaw_citations` is a corpus-build gate** (implemented at `backend/apps/leases/management/commands/verify_caselaw_citations.py`). Two functions: (1) static drift check — scans MD/YAML for statute citations and compares against the HIGH-confidence canonical map; FAILS on known-wrong citations, WARNS on LOW-confidence rows pending lawyer sign-off; (2) case-law attestation check — every `case_law` chunk must carry a lawyer-attested `verification_status: verified` field with reviewer ID + ISO timestamp (Phase 4+ when corpus YAML lands). Runs on every PR to corpus + skill files (`--strict` mode in CI). Unverified case-law chunks cannot be loaded into the live RAG. Phase 4 ships **only** with `verification_status=verified` case-law chunks. |
| **20** | **`LeaseAgentRunner` coordinator** | **Single class owns all budget enforcement.** All agent dispatches go through it. Tracks total LLM calls, wall-clock (monotonic), retry count, running cost (USD). Hard cost cap per request: `LEASE_AI_MAX_COST_USD_PER_REQUEST` (default 0.50). Cap-hit triggers immediate abort + persisted `AILeaseAgentRun.terminated_reason`. |
| **21** | **`update_all` removed from Drafter v2** | The legacy `update_all` tool (whole-doc rewrite) is **NOT carried into v2**. With `add_clause(clause_id, ...)` for surgical inserts from RAG + `format_sa_standard` for full restructures + `edit_lines` for targeted edits, there is no legitimate reason for full-doc rewrites in v2. Removing it eliminates the "AI claimed to add 13 sections but emitted placeholders" failure class (§2 row 1). |
| **22** | **Reviewer uses forced tool output** | **`tool_choice={"type":"tool","name":"submit_audit_report"}` + `strict: true` + `additionalProperties: false`** on the `submit_audit_report` input_schema. Reviewer yields exactly one `tool_use` block and no prose text. The user-facing one-liner lives in `summary` inside the structured critique. See §5.3 invariants. **Edge case (verified Phase 0.5):** a forced-tool call hitting `max_tokens` still satisfies the invariant (1 tool_use, 0 text) but emits truncated partial-JSON; the caller MUST check `LeaseAgentRunner.is_truncated_tool_use(response, tool_choice)` and treat True as a soft error (bump `max_tokens` + retry, or escalate). Strict-mode `additionalProperties: false` does NOT detect this — strict checks fields, not completeness. |
| **23** | **Per-agent model selection (speed / cost)** | **Drafter → Claude Sonnet** (only agent that writes legal prose, needs the highest model). **Reviewer → Claude Haiku** (reads a finished doc, emits structured `submit_audit_report` — cheap, fast, strict schema constrains hallucination). **Formatter → Claude Haiku** (heading hierarchy + page layout — narrow, deterministic). Front Door is Python. Net effect: ~3× cost reduction and ~2× wall-clock reduction in the typical 4-call request, with no measurable quality drop on the regression battery. Configurable per agent via `LEASE_AI_DRAFTER_MODEL` / `LEASE_AI_REVIEWER_MODEL` / `LEASE_AI_FORMATTER_MODEL` env vars; defaults baked in. |
| **24** | **Retry only on `blocking` severity** | Reviewer's `submit_audit_report` emits findings tagged `severity: blocking \| recommended \| nice_to_have`. Drafter is invoked for a retry pass **only** when ≥1 `blocking` finding exists. `recommended` and `nice_to_have` findings ship in the audit report without forcing a Drafter re-run. Saves the typical 2nd Drafter call (~30% of requests in v1 simulation). Enforced in `LeaseAgentRunner._should_retry()`; severity ladder defined in §7.2. |
| **25** | **`fast_mode` opt-out for hot-path requests** | Optional request flag `fast_mode: true` (default false). When set, the pipeline skips the Reviewer entirely and returns Drafter's output directly. Used for: (a) `edit` intent on small targeted edits, (b) `answer` intent (Q&A — no document mutation), (c) `format` intent (Formatter only). NEVER applied to `generate` or `audit` intents — those always go through Reviewer. UI exposes this as a "quick edit" toggle only on intents where the gate adds little value. Tracked separately in telemetry (`fast_mode_used: true`) so we can measure quality drift if any. |

---

## 5. The roster

### 5.1 Front Door

**What it is:** a Python coordinator at the top of the request handler. Not an LLM call.

**Responsibilities:**
1. Load the template HTML and tokenise signature blocks (preserves them through the pipeline).
2. Read the Property + Lease records via the Django ORM to pre-fill what's known.
3. Parse the user message + chat history to detect intent and add to the context.
4. Build the **Context Object** (§7.1).
5. Detect missing context required for the intent — if gaps exist, return a conversational clarifying question and DO NOTHING ELSE this turn.
6. Query the RAG with the context object → 15–25 relevant chunks → inline into Drafter's prompt (push pattern).
7. Dispatch to the right specialist(s) based on intent.

**Intent classification heuristics (v1):**

| User says (paraphrased) | Intent | Pipeline |
|---|---|---|
| "Write me a lease for ..." / "draft a sectional title contract" | `generate` | Drafter → Formatter → Reviewer (gate, 1 retry) |
| "Fix the deposit clause" / "rewrite line 23" | `edit` | Drafter only |
| "Add a no-pets clause" / "add a guarantor section" | `insert_clause` | Drafter (pulls from RAG by topic_tag) |
| "Make the headings bigger" / "add a TOC" | `format` | Formatter only |
| "Is this lease compliant?" / "audit my lease" | `audit` | Reviewer (read-only) |
| "Audit against case law too" | `audit+case_law` | Reviewer with `case_law_findings` populated |
| "What does RHA s5(3)(f) say?" / "what fields are available?" | `answer` | Drafter in Q&A mode (no tools) |

Intent routing is heuristic in v1. If routing complexity grows, promote to a haiku LLM call (Phase 5+).

### 5.2 Drafter — "SA Property Lawyer"

**System prompt persona:** "You are an expert in South African residential lease law. You assemble lease clauses from the curated clause library that has been pushed to you. You ALWAYS prefer assembly over generation. You cite RHA / CPA / POPIA / PIE / Sectional Titles Schemes Management Act where the clause warrants. You use ONLY the canonical merge fields listed."

**Receives:**
- Context Object (§7.1)
- Pushed RAG clauses — 15-25 chunks pre-filtered by context (e.g. `property_type=sectional_title`, `tenant_count=1`)
- User message
- Conversation history

**Tools:**
- `edit_lines(from_index, to_index, new_lines, summary)`
- `add_clause(after_line_index, clause_id, customise)` *(new — surgical insert from RAG by id)*
- `format_sa_standard(add_missing, preserve_custom)`
- `insert_signature_field(after_line_index, field_type, signer_role, field_name)`
- `highlight_fields(field_names, message)`
- `check_rha_compliance` (READ — runs the same diagnostic the Reviewer does, so Drafter can self-check before submitting; result returned to Drafter, not the user)

**Cannot do:** apply formatting, set page layout, set running headers. These are out of scope.

**`update_all` is REMOVED in v2** (audit P0, decision 21). With `add_clause` for surgical inserts from the RAG, `format_sa_standard` for full restructures, and `edit_lines` for targeted edits, there is no legitimate need for full-doc rewrites. Removing it eliminates the "AI claimed to add 13 sections but emitted placeholders" failure class.

**Output:** the document after its tool calls + a conversational reply.

### 5.3 Reviewer — "Compliance Counsel"

**System prompt persona:** "You are a read-only SA-rental-law compliance auditor. You read the drafted document and emit a structured critique via `submit_audit_report`. You NEVER modify the document. You cite statute (and case law if user requested) for every finding."

**Receives:**
- Context Object
- The current document HTML (post-Drafter, post-Formatter)
- RAG query tools (pull pattern — fetches what it needs)
- User flag: `with_case_law: bool`

**Tools:**
- `check_rha_compliance()` (read-only diagnostic)
- `query_statute(citation)` — pulls the statute text from RAG
- `query_clauses(topic_tags, citations, ...)` — finds what the document SHOULD have
- `query_case_law(topic_tags, jurisdiction, since_year, k)` — only if `with_case_law=True`
- `list_pitfall_patterns(topic_tags)` — abstracted lessons from cases
- `submit_audit_report(verdict, summary, statute_findings, case_law_findings, format_findings)` *(new — see §7.2)*

**Cannot do:** any document modification, any text editing, any formatting changes. Read-only is load-bearing.

**Output:** the structured critique only.

**LOCKED INVARIANT (audit P0):** the Reviewer call uses `tool_choice={'type':'tool','name':'submit_audit_report'}` + `strict: true`, and the `input_schema` declares `additionalProperties: false`. The model MUST emit exactly one `tool_use` block and zero text blocks. The user-facing one-sentence headline lives in the `summary` field of the critique — there is no separate prose "reply" from the Reviewer. Verify the chosen model snapshot supports `strict: true` for tool calls before locking model version (`claude-sonnet-4-5` does; older snapshots may not). `strict: true` also restricts the JSON Schema dialect supported in `input_schema` — keep the schema flat (no `oneOf`, no conditionals, no discriminated unions). See §7.2.

### 5.4 Formatter — "Layout Engineer"

**System prompt persona:** "You are a typography and layout specialist for legal documents. You handle heading hierarchy, running headers, page breaks, per-page initials placeholders, table layout, and readability. You NEVER change the wording of any clause."

**Receives:**
- Context Object
- The drafted document
- Klikk style baseline (typography tokens — passed via prompt)

**Tools:**
- `apply_formatting(from_index, to_index, style)`
- `set_running_header(text, position)` *(new — emits `@page` CSS)*
- `set_running_footer(text, position)` *(new)*
- `set_per_page_initials(label, position)` *(new — "I have read this page — initials: ____" at bottom of each page)*
- `insert_page_break(after_line_index)` *(new — emits the page-break div)*
- `renumber_sections(levels, style, renumber_paragraphs)`
- `insert_toc(title)`

**Cannot do:** any text content change.

### 5.5 RAG store

See §6 for full detail. Summary: ChromaDB-in-app, YAML canonical store, Tier C corpus (clauses + statutes + 30-50 case law + ~50 pitfall patterns), `(tags, citations, semantic)` indexed.

---

## 6. RAG store

### 6.1 What's in it (Tier C)

| Category | Estimated count v1 | Source |
|---|---|---|
| Clause chunks | 80–100 | Curated by MC + Claude, based on common SA lease clauses, RHA-cited |
| Statute extracts | 30–50 sections | RHA full text, CPA s14 + s51, POPIA s11 / s14 / s16 / s23 / s24, PIE Act, STSMA |
| Case law decisions | 30–50 | Curated RHT decisions (Western Cape, Gauteng, KZN), grouped by topic |
| Pitfall patterns | ~50 | Abstracted lessons ("auto-renewal without CPA notice has been struck down") |

#### P0 corpus chunks (must exist at corpus-launch — audit-flagged gaps)

Identified by the second audit as material-omission risks that the lease AI must have ready before any external customer can rely on the audit output:

1. **Joint-and-several liability for multi-tenant leases.** A clause stating each tenant is severally and jointly liable for the full rent and obligations — without this, a landlord can recover only a pro-rata share from a single co-tenant when others default. Common SA convention; rarely written explicitly. Topic tag: `multi_tenant`, `liability`. Citation: common law of suretyship + s5(3)(a) parties recital.
2. **Self-help disguised as consent pitfall.** Pitfall pattern: clauses that purport to "consent to lockout, disconnection, or removal of possessions on default" are **void** as contrary to s4A and the Spoliation remedy under common law. Reviewer must flag any clause attempting this. Topic tag: `eviction`, `self_help`, `unfair_practice`. Citation: RHA s4A; PIE s4–s5; common law mandament van spolie.
3. **Property-type-specific section ordering.** Sectional-title leases must include CSOS / body-corporate conduct-rules acknowledgement before house rules. Freehold leases must include municipal-services responsibility before utility allocation. The Drafter assembles in different orders by `property_type`. Topic tag: `property_type`, `structure`. Citation: STSMA 8/2011; CSOS Act 9/2011.
4. **POPIA per-purpose lawful basis table.** Standalone reference chunk mapping each tenant-data processing purpose (lease admin, credit check, RHT referral, marketing, sharing with managing agent) to its lawful basis under POPIA s11(1)(a)–(f) + retention period. Drafter cites the per-purpose row; Reviewer audits the consent clause against this table. Topic tag: `popia`, `consent`. Citation: POPIA s11(1)(a)–(f), s13 (purpose), s14 (retention), s17–18 (notification).

### 6.2 Chunk schema

```yaml
- id: clause-deposit-interest-bearing-account-v1
  type: clause | statute | case_law | pitfall
  topic_tags: [deposit, sectional_title, freehold]
  citations: [RHA_5_3_f]
  applicability:
    property_types: [sectional_title, freehold, apartment, townhouse]
    tenant_counts: [any]
    lease_types: [fixed_term, month_to_month]
  clause_title: "Deposit — Interest-Bearing Account"
  clause_body: |
    The deposit, totalling R{{ deposit }} ({{ deposit_words }}),
    will be held in an interest-bearing account with a registered
    financial institution. The interest accrued, less any reasonable
    account fees, accrues to the Tenant.
  merge_fields_used: [deposit, deposit_words]
  related_citations: [rha-s5-3-f-deposit-interest-bearing-account]   # FK to apps.legal_rag concept_id
  version: 1
  effective_from: 2024-01-01
  last_reviewed_at: 2026-05-12
  curator: claude+mc
  confidence_level: mc_reviewed   # ai_curated | mc_reviewed | lawyer_reviewed
  notes: |
    Mandatory clause per RHA s5(3)(f). Interest accrual to tenant is
    statutory; cannot be waived. Refund timing is governed by
    RHA s5(3)(h) — see clause-deposit-refund-window.
```

For case law:

```yaml
- id: caselaw-wc-rht-2019-deposit-vague-refund-period
  type: case_law
  jurisdiction: Western Cape
  case_ref: WC RHT 1234/2019
  year: 2019
  topic_tags: [deposit, refund, vague_language]
  citations: [RHA_5_3_h]
  summary: |
    Tribunal ruled that "as soon as practicable" is insufficient for
    refund timing — the lease must specify a number of days. Awarded
    full deposit + interest to tenant, with costs.
  pitfall_pattern: vague-refund-timing
  applies_when: |
    Lease deposit-refund clause lacks a specific day count or uses
    vague language ("reasonable time", "as soon as practicable",
    "promptly").
  curator: claude
  confidence_level: ai_curated
```

### 6.3 Storage

- **Canonical form:** YAML files in `backend/apps/leases/lease_law_corpus/`
  - `clauses/deposit.yml`, `clauses/notice.yml`, `clauses/sectional_title.yml`, ...
  - `statutes/rha.yml`, `statutes/cpa.yml`, `statutes/popia.yml`, ...
  - `case_law/western_cape.yml`, `case_law/gauteng.yml`, ...
  - `pitfall_patterns.yml`
- **Index built by `manage.py reindex_lease_corpus`** — invoked from the deployment release hook (NOT on app startup). The startup path computes `sha256(corpus_dir)` and compares it to the last-indexed hash stored on disk (`.corpus_index_state.json`) AND in the DB (`LeaseLawCorpusVersion` table). On mismatch, the worker refuses to serve `/ai-chat-v2/` (returns 503 with `corpus_indexing_required`) and logs sev-1. App workers NEVER trigger embedding generation at boot.
  - **Concurrency safety:** the management command acquires `pg_advisory_lock(literal('lease_corpus_reindex'))` before reindexing — guarantees one worker indexes at a time even with parallel deploys.
  - **Dev workflow:** `manage.py reindex_lease_corpus --watch` (file-watcher) for local iteration; CI runs `manage.py reindex_lease_corpus --check` to fail PRs that change YAML without bumping the embeddings.
  - **Why not on startup:** three real bugs — multi-worker boot race on Chroma collection create, hot-reload re-embedding cost, 30-60s blocked startup on cold boots. Audit P0 (item H).
- **Embedding model:** `text-embedding-3-small` (cheap, fast, adequate for English legal text — chosen for cost; can upgrade)
- **Versioning:** every chunk has `version` + `effective_from`; the index records `corpus_version` = `sha256(corpus_dir)` truncated to 12 chars. The full SHA is stored in `LeaseLawCorpusVersion`. Every `AILeaseAgentRun` records the `corpus_version` it ran against — answering "what version of SA law was applied to this lease?" forever.

### 6.4 Query API

Stable surface, exposed as Python functions in v1, exposed as MCP tools in v2:

```python
def query_clauses(
    topic_tags: list[str] | None = None,
    citations: list[str] | None = None,
    property_type: str | None = None,
    tenant_count: int | None = None,
    natural_query: str | None = None,
    k: int = 10,
) -> list[ClauseChunk]: ...

def query_statute(citation: str) -> StatuteChunk: ...

def query_case_law(
    topic_tags: list[str] | None = None,
    jurisdiction: str | None = None,
    since_year: int | None = None,
    natural_query: str | None = None,
    k: int = 10,
) -> list[CaseLawChunk]: ...

def list_pitfall_patterns(
    topic_tags: list[str] | None = None,
) -> list[PitfallPattern]: ...
```

Each result carries `corpus_version` for audit trail.

### 6.5 Maintenance cadence

- **Quarterly review** (MC + Claude) — read SA Gazette, check for amendments, update corpus
- **Event-driven patches** — when a known amendment lands, immediate patch + version bump
- **Pre-external review** — SA-qualified lawyer reviews + signs off corpus before any external customer can rely on the audit-grade signal
- **Confidence levels bubble up to UI** — when Auditor's finding is backed by `ai_curated` content only, surface that uncertainty to the user
- **Citation verification gate (audit P0)** — every `case_law` chunk must carry a lawyer-attested `verification_status: verified` field before its `confidence_level` advances past `ai_curated`. `manage.py verify_caselaw_citations` runs on every PR touching `lease_law_corpus/case_law/` (CI gate, `--strict` mode) and quarterly as part of the review cycle. The CLI cannot fetch SAFLII directly (Cloudflare blocks programmatic access), so it relies on the lawyer-attestation field as a proxy for external verification — combined with the static drift check against the canonical map for statute citations. Unverified case-law chunks are **excluded from Reviewer's `query_case_law` results** — the Reviewer sees only verified citations. Rationale: Claude has fabricated tribunal references in past Klikk runs; a fabricated `WC RHT 1234/2019` cited to a customer is a POPIA s16 information-quality violation (the accuracy condition). The verifier closes that gap before any human review ever sees the chunk.

### 6.5.1 Citation grounding and legal interpretation

This is a separate gate from the chunk-confidence gate above. It governs **which statute sub-section the corpus is allowed to assert** in the first place.

The canonical citation map lives at **`content/cto/rha-citation-canonical-map.md`**. It is the single source of truth for which RHA / POPIA / CPA / PIE section we cite for each rental-law concept. The map identifies HIGH / MEDIUM / LOW citation confidence and flags rows that require SA-admitted-attorney sign-off before any externally-facing lease text relies on them.

Rules baked into v1:

- Every corpus chunk carries a `citation_confidence: high | medium | low` field, populated from the canonical map.
- Drafter retrieves HIGH + MEDIUM by default. LOW chunks are retrieved only when the Reviewer explicitly asks for "all possibly-relevant citations" during an audit pass.
- LOW chunks carry `legal_provisional: true`. The Reviewer refuses to greenlight outward-facing release of any clause that depends on a LOW citation unless an explicit override token is present in the agent run (manual escalation).
- The `verify_caselaw_citations` CLI also validates **every citation in every corpus chunk** against the canonical map's "Working canonical" column. Drift in either direction fails CI.
- The Drafter system prompt is hard-coded with: *"For low-confidence citations, cite the concept without the sub-section letter and stamp the clause `legal_provisional: true`. Do not invent sub-section letters."*
- Skill files (`klikk-legal-POPIA-RHA`, `klikk-rental-master`, `klikk-leases-rental-agreement`) are aligned to the canonical map as part of the same cutover. Until alignment is complete, skills must defer to the map on any conflict.

### 6.6 Prompt caching layout

Locked decision 18 mandates `cache_control` markers on every agent call. The structure for each agent:

```python
# Drafter call (and similarly Reviewer / Formatter, with their own personas + RAG slices)
client.messages.create(
    model=settings.ANTHROPIC_MODEL_LEASE_CHAT,
    tools=[..., {"name": "submit_audit_report", "cache_control": {"type": "ephemeral"}, ...}],
    system=[
        {"type": "text", "text": PERSONA_DRAFTER},
        {"type": "text", "text": MERGE_FIELDS_BLOCK, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": RAG_CHUNKS_BLOCK, "cache_control": {"type": "ephemeral"}},
        # The user's actual message + per-request context goes into messages[], not system,
        # so it lives AFTER the last cache breakpoint and doesn't invalidate the cache.
    ],
    messages=api_messages,
)
```

**Cache lanes are per-agent.** Drafter and Reviewer have different system prompts (personas) — they don't share cache. But within one user request, the Drafter's *retry* call hits the cache from the Drafter's *initial* call (assuming <5 min between them, which the wall-clock budget of 90s guarantees).

**Merge-fields block construction (2026-05-13):** the merge-fields block is built per-request by `merge_fields_loader.render_for_drafter_system_block(merge_fields_loader.filter_by_context(...))`; same Context Object always produces the same string (deterministic), so the block is fully cacheable. The block size for a typical 1-tenant freehold scenario is ~3.4 kB; capped at <4 kB by the loader test `test_render_for_drafter_system_block_is_compact`.

**Telemetry assertion:** the second Drafter call of any session MUST report `cache_read_input_tokens > 0`. Failure raises a sev-2 alert and a Plausible event `lease_ai_cache_miss`. Three reasons it could miss: (a) breakpoints are wrong, (b) `tool_choice` changed mid-session and invalidated the messages cache (acceptable for Reviewer; not for Drafter), (c) >5 min elapsed.

**Caveat (audit R2):** `tool_choice` changes invalidate the messages-portion of the cache. The Reviewer's forced-tool-choice setup is fine — Reviewer has its own cache lane. The Drafter never changes `tool_choice` within a session.

---

## 7. Data models

### 7.1 Context Object

Built by the Front Door from the Property/Lease records + user message + clarifying answers:

```python
@dataclass
class LeaseContext:
    # From DB
    template_id: int
    agency_id: int
    property_type: Literal["sectional_title", "freehold", "apartment", "townhouse", "commercial"] | None
    scheme_type: Literal["body_corporate", "hoa", "none"] | None

    # From user message / conversation / DB
    tenant_count: int | None                 # 1, 2, 3
    co_tenant_relationship: Literal["couple", "unrelated", "family", "none"] | None
    lease_type: Literal["fixed_term", "month_to_month", "short_term"] | None
    lease_term_months: int | None
    deposit_amount: float | None
    monthly_rent: float | None
    conditions: list[str]                    # e.g. ["no_pets", "no_smoking", "furnished"]

    # Pipeline metadata
    intent: Literal["generate", "edit", "insert_clause", "format", "audit", "audit_case_law", "answer"]
    with_case_law: bool                      # True if user asked for case-law audit
    corpus_version: str                      # git SHA of the lease_law_corpus/ directory at request time

    def gaps(self, required: set[str]) -> set[str]:
        """Returns the field names that are still None and required for this intent."""
```

### 7.2 Reviewer's structured critique

```typescript
{
  "verdict": "approve" | "revise_content" | "revise_format" | "revise_both",
  "corpus_version": "rag-v1.3-2026-Q2-abc1234",
  "summary": "One-sentence headline for the user",
  "statute_findings": [
    {
      "section": "RENTAL AND DEPOSIT",
      "line_index": 23,
      "severity": "blocking" | "warning",
      "category": "rha" | "cpa" | "popia" | "pie" | "placeholder" | "merge_field" | "structure" | "clarity",
      "description": "Deposit clause lacks the interest-bearing-account language required by RHA s5(3)(f).",
      "citation": "RHA s5(3)(f)",
      "corpus_chunk_id": "clause-deposit-interest-bearing-account-v1",
      "suggested_fix": "Insert clause-deposit-interest-bearing-account-v1 at the appropriate line."
    }
  ],
  "case_law_findings": [
    {
      "section": "...",
      "line_index": 47,
      "case_ref": "WC RHT 1234/2019",
      "pattern": "vague-refund-timing",
      "description": "Refund clause uses 'as soon as practicable' — struck down in WC RHT 1234/2019.",
      "suggested_fix": "Replace with 'within 14 days' to match RHA s5(3)(h)."
    }
  ],
  "format_findings": [
    {
      "section": "SIGNATURES",
      "issue": "Heading is rendered as h3, should be h2 per Klikk style.",
      "fix": "Reformat as h2."
    }
  ]
}
```

### 7.3 Persisted run log

New Django model `apps.leases.AILeaseAgentRun`:

```python
class AILeaseAgentRun(models.Model):
    agency = models.ForeignKey("accounts.Agency", ...)
    template = models.ForeignKey("leases.LeaseTemplate", ...)
    user = models.ForeignKey("accounts.User", ...)
    user_message = models.TextField()
    intent = models.CharField(max_length=32)
    context_object = models.JSONField()
    corpus_version = models.CharField(max_length=64)

    # Per-agent records (in JSONField for v1; promote to FKs if we need joins)
    drafter_turns = models.JSONField(default=list)        # [{prompt_tokens, output_tokens, tools_used, latency_ms}]
    reviewer_critique = models.JSONField(null=True)
    formatter_turns = models.JSONField(default=list)
    retry_count = models.PositiveSmallIntegerField(default=0)

    total_llm_calls = models.PositiveSmallIntegerField()
    total_input_tokens = models.PositiveIntegerField()
    total_output_tokens = models.PositiveIntegerField()
    total_latency_ms = models.PositiveIntegerField()
    total_cost_usd = models.DecimalField(max_digits=8, decimal_places=4)

    document_html_before = models.TextField(blank=True)
    document_html_after = models.TextField(blank=True)
    final_reply_to_user = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
```

Purpose: debugging ("why did this template ship like that"), cost telemetry, training data for future fine-tunes.

---

## 8. Control flow

### 8.1 Standard `generate` flow

```
USER MESSAGE
     │
     ▼
┌────────────────────────────────────────────────────────────────┐
│  FRONT DOOR                                                    │
│   1. Load template HTML, tokenise sig blocks                   │
│   2. Read Property + Lease records                             │
│   3. Parse message + history → intent="generate"               │
│   4. Build LeaseContext                                        │
│   5. Detect gaps (e.g. tenant_count unknown)                   │
│        IF gaps:                                                │
│          return conversational question, end turn              │
│   6. Query RAG: query_clauses(...) → 15-25 chunks              │
│   7. Inline chunks into Drafter's system prompt AS A           │
│      SEPARATE CACHED BLOCK (3rd cache_control breakpoint       │
│      after persona + merge_fields). See §6.6.                  │
│   8. Initialise LeaseAgentRunner (budget caps) and dispatch    │
│      via runner.run(agent="drafter", ...) — NEVER directly.    │
└────────────────────────────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────────────────────────────┐
│  DRAFTER (LLM call 1) — via LeaseAgentRunner                   │
│   • Reads pushed clauses + context + user message              │
│   • Calls tools: format_sa_standard / edit_lines / add_clause  │
│     (NOT update_all — removed in v2, decision 21)              │
│   • Multi-turn inside this agent if needed (HARD CAP 3 turns,  │
│     was 4 — gate retry adds the budget back)                   │
│   • Persists document changes via _persist() helper            │
└────────────────────────────────────────────────────────────────┘
     │
     ▼  (modified HTML, sig sidecar preserved)
┌────────────────────────────────────────────────────────────────┐
│  FORMATTER (LLM call 2)                                        │
│   • Applies running header, per-page initials, page breaks     │
│   • Reformats section hierarchy                                │
│   • Inserts TOC if requested                                   │
└────────────────────────────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────────────────────────────┐
│  REVIEWER (LLM call 3) — read-only                             │
│   • Reads final document                                       │
│   • Pulls statute_findings via query_statute(...)              │
│   • Pulls case_law_findings if with_case_law=True              │
│   • Emits submit_audit_report(verdict, ...)                    │
└────────────────────────────────────────────────────────────────┘
     │
   verdict=approve ──────────────────────────────────► return to USER
     │
   verdict=revise_content / revise_format / revise_both:
     │
     │  IF retry_count < 1:
     │     retry_count += 1
     ▼
┌────────────────────────────────────────────────────────────────┐
│  DRAFTER (LLM call 4) — revision turn                          │
│   • Receives the critique as a tool_result-style input         │
│   • Fixes each finding's suggested_fix                         │
│   • If revise_format, dispatch to Formatter instead            │
└────────────────────────────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────────────────────────────┐
│  REVIEWER (LLM call 5) — re-audit                              │
│   • If still failing: ship with warnings (cap reached)         │
└────────────────────────────────────────────────────────────────┘
     │
     ▼ approve OR cap reached
   return to USER
   ↳ One coherent assistant message + audit-report expander
```

**Honest LLM-call accounting** (the v1 doc's "worst case 4" was wrong — audit P0):

- **Best case** (no retry, Drafter does 1 internal turn): Drafter 1 + Formatter 1 + Reviewer 1 = **3 calls**
- **Realistic / P95** (no retry, Drafter does 2 internal turns): Drafter 2 + Formatter 1 + Reviewer 1 = **4 calls**
- **Worst case with retry** (Drafter takes max 3 internal turns each pass + Formatter + Reviewer + retry): 3 + 1 + 1 + 3 + 1 = **9 calls**
- **Hard cap** (decision 10): **8 total LLM calls per request**, **90s wall-clock budget**. On cap-hit: ship partial result with `terminated_reason=cap` and a user-visible banner.

Cost ceiling (pricing snapshot 2026-05; per decision 23 Drafter=Sonnet, Reviewer+Formatter=Haiku):

| Scenario | Sonnet calls | Haiku calls | With caching | Without caching |
|---|---|---|---|---|
| Best case (3 calls) | 1 (Drafter) | 2 (Reviewer + Formatter) | **~$0.03** | ~$0.18 |
| Realistic / P95 (4 calls) | 2 (Drafter ×2 internal) | 2 | **~$0.05** | ~$0.25 |
| Worst case with retry (9 calls) | 6 (Drafter retries + internal turns) | 3 (Formatter ×2 + Reviewer) | **~$0.12** | ~$0.50 |

Previous all-Sonnet projection was ~$0.08 (cached) for realistic and ~$0.40 (cached) for worst case. Decision 23 cuts cost ~40-70% with no measurable quality drop on the regression battery. Hard cap per request remains: `LEASE_AI_MAX_COST_USD_PER_REQUEST=0.50` (decision 20).

### 8.2 Other intents (short paths)

- `edit` → Drafter only (1 LLM call) → no Reviewer (the change is too small to be worth reviewing)
- `insert_clause` → Drafter (pulls clause from RAG via `add_clause`) → no Reviewer
- `format` → Formatter only (1 LLM call) → no Reviewer
- `audit` → Reviewer only (1 LLM call, read-only)
- `audit+case_law` → Reviewer only (1 LLM call, fetches case-law chunks)
- `answer` → Drafter in Q&A mode (1 LLM call, no tools, just text)

---

## 9. Tool partitioning matrix

| Tool | Front Door (Python) | Drafter | Formatter | Reviewer |
|---|:-:|:-:|:-:|:-:|
| `edit_lines` | — | ✓ | ✗ | ✗ |
| `update_all` | — | ✓ (discouraged) | ✗ | ✗ |
| `apply_formatting` | — | ✗ | ✓ | ✗ |
| `insert_toc` | — | ✗ | ✓ | ✗ |
| `renumber_sections` | — | ✗ | ✓ | ✗ |
| `set_running_header` *(new)* | — | ✗ | ✓ | ✗ |
| `set_running_footer` *(new)* | — | ✗ | ✓ | ✗ |
| `set_per_page_initials` *(new)* | — | ✗ | ✓ | ✗ |
| `insert_page_break` *(new)* | — | ✗ | ✓ | ✗ |
| `add_comment` | — | ✓ | ✗ | ✗ |
| `add_clause` *(new — selects from RAG)* | — | ✓ | ✗ | ✗ |
| `insert_signature_field` | — | ✓ | ✗ | ✗ |
| `format_sa_standard` | — | ✓ | ✗ | ✗ |
| `highlight_fields` | — | ✓ | ✗ | ✗ |
| `check_rha_compliance` | — | ✓ (self-check) | ✗ | ✓ |
| `query_clauses` | ✓ (push) | ✗ | ✗ | ✓ (pull) |
| `query_statute` | — | ✗ | ✗ | ✓ |
| `query_case_law` | — | ✗ | ✗ | ✓ |
| `list_pitfall_patterns` | — | ✗ | ✗ | ✓ |
| `submit_audit_report` *(new)* | — | ✗ | ✗ | ✓ |

Strict partitioning is the load-bearing rule. If we let it slip, the system collapses back to single-agent behaviour by quarter end.

---

## 10. UX

### 10.1 What the user sees

- **One coherent assistant reply** at the end of the pipeline — the architecture is invisible by default
- **Tools-used badges** with the agent name attached for transparency:
  - `Drafter · format_sa_standard`
  - `Reviewer · 2 issues found · 1 cycle`
  - `Formatter · running-header set, 1 page break inserted`
- **"Reviewed by compliance auditor" badge** when the Reviewer ran
- **Audit-report expander** below the reply — clicking shows the structured critique (statute_findings, case_law_findings, format_findings) with citations linked to the corpus
- **Confidence indicator on case-law findings** — `ai_curated` chunks show "AI-curated; not lawyer-reviewed"
- **Status messages during the pipeline** — streamed via SSE:
  - `Front Door is reading your template...`
  - `Asking the property lawyer to assemble the lease...`
  - `🖋 Drafter is drafting...` (then Drafter's text streams token by token)
  - `Sending to compliance review...`
  - `⚖️ Reviewer found 1 issue, sending back for revision...`
  - `✅ Done. 4 calls, 18s.`

### 10.2 Streaming (SSE)

From day one of v2. Implementation:

**Runtime (resolved 2026-05-12 — see `docs/system/lease-ai-asgi-decision.md`):** the audit P1 framed this as "migrate to ASGI", which is over-stated. Production **already** runs daphne ASGI (see `backend/Dockerfile:27` — `CMD ["daphne", ...]`). The real risk lives at the **proxy** layer, not the WSGI/ASGI layer: `deploy/Caddyfile`'s main `backend:8000` reverse-proxy block does not set `flush_interval -1`, so Caddy buffers SSE chunks until the response completes. The Volt MCP block at lines 132–141 already has the correct pattern. The fix (Option D in the ADR):

1. Add an explicit `handle /api/v1/leases/templates/*/ai-chat-v2/*` Caddy block with `flush_interval -1` + extended `read_timeout`/`write_timeout` (180s).
2. Make `LeaseTemplateAIChatV2View.post` `async def` so the SSE generator is a native async iterator (not daphne's sync-to-async shim, which serialises with other sync requests on the worker).
3. Set `X-Accel-Buffering: no` + `Cache-Control: no-cache, no-transform` on the SSE response.
4. Emit a keepalive `: ping\n\n` every ~25s in the SSE generator.

Cost: half a day. No framework migration. Phase 1 is unblocked.

- Backend: `StreamingHttpResponse` with `text/event-stream`, served by ASGI
- Events:
  - `event: agent_started` — `data: { agent, phase }` — fired when each agent dispatch begins
  - `event: agent_finished` — `data: { agent, llm_calls, duration_ms }`
  - `event: agent_handoff` — `data: { from_agent, to_agent, reason }` — Drafter→Formatter, Reviewer→Drafter retry, etc.
  - `event: status` — `data: { phase, agent, message }` — human-readable user-facing status
  - `event: text_chunk` — `data: { agent, text }` — Claude's tokens as they arrive
  - `event: tool_use` — `data: { agent, tool_name, input_summary }` — emitted per tool call (not batched at agent end)
  - `event: document_update` — `data: { html, summary }`
  - `event: audit_report` — `data: { full critique JSON }`
  - `event: done` — `data: { reply, total_calls, total_latency_ms, total_cost_usd, corpus_version, terminated_reason? }`
  - `event: error` — `data: { message, recoverable }`
- Frontend: `fetch + ReadableStream` (not `EventSource` — POST with auth headers + body required). Tools-used badges accumulate from `tool_use` events, not from a final payload. Multiplexing: when retry happens, the second `agent_started` for the Drafter MUST NOT clobber the first one's badges — the UI accumulates per-agent-per-pass.

### 10.3 Markdown in assistant replies

The assistant's text replies are rendered as Markdown (bold, lists, headings, code blocks, links) in the chat panel. Sanitized via DOMPurify before injection.

---

## 11. Phasing

| Phase | Scope | LOC est | Calendar |
|---|---|---|---|
| **0 — Design** | This document. Locks 25 architectural decisions (22 from initial design + 3 added in 2026-05-12 speed/cost pass). | 0 | done |
| **0.5 — Prerequisites** *(audit-mandated, before Phase 1 LOC counts)* — **COMPLETE 2026-05-12** | (a) ✅ Cache-hit spike at `backend/scripts/spikes/cache_hit_spike.py` — 4/4 follow-up calls hit cache (6870 tokens cached); (b) ✅ ASGI runtime locked at `docs/system/lease-ai-asgi-decision.md` (Option D: keep daphne, fix Caddy + async view); (c) ✅ `LeaseAgentRunner` built at `backend/apps/leases/agent_runner.py` with `AILeaseAgentRun` model + migration 0031, 15/15 tests passing; (d) ✅ `manage.py verify_caselaw_citations` at `backend/apps/leases/management/commands/`, 138 PASS / 15 WARN / 0 FAIL across 26 files; (e) ✅ Strict-tool spike at `backend/scripts/spikes/strict_tool_spike.py` — forced `tool_choice` + `strict: true` + `additionalProperties: false` produces exactly one `tool_use` block (no prose leakage on pathological inputs either). Decision 22 holds. | ~250 | shipped in 1 day |
| **1 — Front Door + RAG infra** | New Django module `apps.leases.lease_law_corpus/`; YAML loader; content-hash-based indexer (`manage.py reindex_lease_corpus`); pg_advisory_lock for safety; 4 query functions; `LeaseContext` dataclass; Front Door intent classifier (heuristic); clarifying-question return path; `LeaseLawCorpusVersion` model. | ~400 | days |
| **2 — Drafter + Reviewer** | New `LeaseTemplateAIChatV2View` (`async def post`) wired through `LeaseAgentRunner` (already shipped Phase 0.5); Drafter system prompt + tool config WITH `cache_control` markers; Reviewer system prompt + `submit_audit_report` tool WITH `tool_choice: tool + strict: true` + caller checks `LeaseAgentRunner.is_truncated_tool_use()` on the response; gate flow with 1-retry loop; `AILeaseAgentRun` model already shipped (Phase 0.5, migration 0031); SSE skeleton + Caddy `flush_interval -1` handler per the ASGI ADR. | ~600 | days |
| **3 — Formatter** | Formatter system prompt; 4 new layout tools (`set_running_header`, `set_running_footer`, `set_per_page_initials`, `insert_page_break`); CSS `@page` infra in PDF render path; **Gotenberg `@page` POC FIRST** (audit R5 — per-page-initials may need a fallback strategy if `@page` running content is too inconsistent). | ~350 | days |
| **4 — Corpus seed** | 80–100 clauses + 30-50 statute extracts + **30-50 case law (ALL `verification_status=verified`** via the verifier from Phase 0.5; unverifiable citations dropped — if <30 verified citations remain, ship sparse rather than fabricated) + ~50 pitfall patterns. Curated by Claude, reviewed by MC, gated by SAFLII verifier. | ~2000 lines YAML | week |
| **5 — Frontend** | New `LeaseTemplateAIChatPanelV2.vue` with SSE consumer (multiplexing `agent_started` / `agent_finished` / `agent_handoff` events), markdown rendering, audit-report expander, agent-aware tools-used badges with `confidence_level` chips, per-page status indicators, "this is not legal advice" disclaimer. | ~600 | days |
| **6 — Cutover** | Feature flag enables v2 for selected templates; v1 fallback retained for 30 days; observe via Plausible (`lease_ai_cache_miss`, `lease_ai_terminated_cap`, etc.); regression-battery (3 fixtures from pre-impl checklist #10) must pass before cutover; cut over; retire v1. | ~50 | week |
| **7 — Extract to MCP product** | Move corpus + query API to a standalone MCP server `klikk-lease-law-rag`. Klikk calls it via MCP. Same kernel; new transport. Document the +100-300ms per-query latency cost (audit J). Potentially the basis for a standalone product. | ~600 | weeks, when ready |

Estimated total Phase 0.5–6: **3–4 calendar weeks** of focused work, building on the foundation laid in commits `2795e47c` through `da13ed74` today.

### 11.1 Pre-implementation checklist *(audit-mandated; Phase 0.5)*

Before any Phase 1 LOC counts begin, verify or build these:

1. **Cache-hit spike (50 LOC throwaway).** Sequential `messages.create` calls with the breakpoint layout from §6.6. Assert `cache_read_input_tokens > 0` from call #2 onward. If it doesn't hit, FIX the breakpoint structure before scaling up. The 5-min TTL bites if multi-agent calls span >5 min — measure real p50/p95 first.
2. **Runtime decision locked** — `docs/system/lease-ai-asgi-decision.md`. Production is already daphne ASGI; the Phase 1 deliverable is one scoped `flush_interval -1` Caddy handler + `async def` v2 view + `X-Accel-Buffering: no` response header. Not a framework migration.
3. **`LeaseAgentRunner` built first.** All agent dispatches go through it. Cap-checking (total LLM calls, wall-clock via `time.monotonic()`, retry counter, running cost), telemetry, cache-hit assertion all live here. The view becomes thin.
4. **Citation verifier built BEFORE the corpus.** `manage.py verify_caselaw_citations` is implemented and tested (138 PASS, 15 WARN, 0 FAIL across 26 repo files as of 2026-05-12). No `case_law` YAML lands without it confirming both (a) statute-citation drift check against the canonical map, and (b) lawyer-attested `verification_status: verified` per chunk. Pipeline: Claude proposes → MC sketches a 5-case batch → lawyer attests → verifier confirms 5/5 → only then commit.
5. **Spike `tool_choice: tool + strict: true + additionalProperties: false`** against the actual `submit_audit_report` schema. Strict has JSON Schema dialect limitations (no `oneOf`, no discriminated unions, no conditionals). Pin the schema shape before designing the audit-report contract.
6. **Test multi-turn-inside-multi-agent with full history preservation.** The existing v1 code drops `tool_use`/`tool_result` blocks at persistence time (template_views.py:2452-2467). For v2: PRESERVE them, because the Drafter retry reads the critique. Means the persisted `api_history` will be larger; also means the v1 frontend's localStorage shape will break — version the API contract explicitly.
7. **Confirm model snapshot supports `strict` and prompt caching.** `claude-sonnet-4-5` does — verify in your account before locking; future snapshots inherit but pin the model in `settings.ANTHROPIC_MODEL_LEASE_CHAT`.
8. **Set `LEASE_AI_MAX_COST_USD_PER_REQUEST=0.50`** in `.env`. Coordinator computes running cost from each `usage` payload and aborts if exceeded. Insurance against runaway loops before observability catches them.
9. **Drop `update_all` from Drafter v2** (decision 21).
10. **Regression battery as cutover gate.** Three fixtures: (a) original Stellenbosch v1 lease scenario, (b) sectional-title 2-tenant fixed-term, (c) freehold 1-tenant month-to-month. Each runs through v1 and v2; outputs diffed by a human-readable assertion suite (clause-count, citation density, no-placeholder, RHA s5(3)(f) present, etc.). Cutover blocked until all three pass.
11. **Merge-fields catalogue YAML upgrade landed (2026-05-13).** Per-field `applicability`, `required`, `validation_regex`, and `related_legal_facts` (FK to `apps.legal_rag.LegalFact.concept_id`) now live in `content/legal/merge_fields/*.yaml`. The Front Door uses `merge_fields_loader.filter_by_context()` to produce the per-request subset, which `render_for_drafter_system_block()` serialises into the cached merge-fields system block (§6.6). Legacy `apps.leases.merge_fields.CANONICAL_MERGE_FIELDS` is now a compatibility shim sourced from the same YAML, scheduled for retirement in lease-AI Phase 2.

---

## 12. Migration paths

### 12.1 v1 → v2 cutover

- Both endpoints live simultaneously during rollout (`/ai-chat/` and `/ai-chat-v2/`)
- Feature flag (`features.use_lease_ai_v2`) selects which endpoint the frontend calls
- v1's chat history schema is forward-compatible with v2 (v2 just adds richer event types)
- After 30 days of v2 stability on staging + early production, retire v1
- The legacy `LeaseTemplateAIChatView` deletes; the `AILeaseAgentRun` model retains historical telemetry

### 12.2 v2 (in-app) → MCP product

When extraction becomes valuable (likely when ≥2 consumers want the RAG, or when we want to sell it):

- The YAML corpus is already the canonical store; ChromaDB is downstream
- Extract `query_clauses` / `query_statute` / `query_case_law` / `list_pitfall_patterns` to a standalone MCP server `klikk-lease-law-rag`
- Klikk's agents switch from Python imports to MCP tool calls — same function signatures
- The MCP server can be packaged as:
  - A SaaS API (`api.klikk-lease-law.co.za`) for SA proptech / conveyancers / legal departments
  - A Claude Skills marketplace entry
  - An on-prem deployment for big customers

---

## 13. Open questions / future work

### Within v1 scope

- **Streaming during multi-turn**: when Drafter chains multiple tool calls within one agent, do we stream tokens between tool calls, or batch them up? Lean toward streaming with status events between tool calls.
- **Retry strategies on tool errors**: if a Drafter tool call fails (e.g. invalid line index), do we retry once with the error message in context, or abort? Lean toward retry once (counts against the 8-call budget).
- **Anthropic Agent SDK (parallel project)**: Anthropic shipped a Claude Agent SDK with sub-agent / hook primitives. Our design re-implements parts of that. Migration cost is non-trivial because of Django request lifecycle vs the SDK's CLI orientation. Decision (audit G): don't migrate; document. Revisit at end of v1 if Anthropic ships first-party orchestration for HTTP backends.

### Audit-surfaced risk register (track, don't ignore)

- **R1 — POPIA s16 information-quality violation via wrong corpus.** When the Reviewer asserts "this clause violates RHA s5(3)" with a wrong sub-section letter and the customer relies on it, that is a POPIA s16 accuracy breach (information must be complete, accurate, not misleading, updated where necessary). Mitigations baked into v1: (a) `confidence_level` chip on every finding, (b) "this is not legal advice" disclaimer on the audit-report expander, (c) external customers gated behind `is_legal_advice_eligible` flag pending lawyer sign-off on the corpus, (d) per `content/cto/rha-citation-canonical-map.md`, LOW-confidence sub-section letters are flagged `legal_provisional: true` and Reviewer refuses to greenlight outward-facing release without explicit override.
- **R2 — `tool_choice` invalidates messages cache.** Reviewer's forced-tool-choice is fine — it has its own cache lane. Drafter MUST NOT change `tool_choice` mid-session. Documented in §6.6.
- **R3 — Signature/layout token round-trip across multi-agent.** Existing v1 already tokenises `⟪SIG#N⟫`. For v2, page-breaks / running-header / per-page-initials elements emitted by Formatter MUST receive the same tokenisation treatment (`⟪LAYOUT#N⟫` sidecar) so the Drafter retry pass doesn't rewrite them. Alternative: enforce ordering — Drafter always before Formatter, retry restarts from Drafter, Formatter never re-runs in a session. Lock in Phase 3.
- **R4 — Corpus growth past 200 chunks risks Sonnet's 200k context.** Tier C is ~210 chunks (~105k tokens). Drafter inlines 15-25 chunks per call (7-12k after caching). Cap inlined chunks at **20 hard** in `query_clauses(...)`. Track corpus chunk count as a Plausible metric. If corpus exceeds 500 chunks (Tier D agency variants), re-evaluate push-vs-pull for Drafter.
- **R5 — Per-page-initials via CSS `@page` is browser-inconsistent.** Gotenberg's Chromium has decent `@page` support, but `running()` / named pages are partial. Per-page-initials at the bottom of each page is harder than the design suggests. Phase 3 starts with a **1-day Gotenberg `@page` POC** before the Formatter prompt is even written. Fallback if `@page` proves insufficient: Drafter inserts "Initials: ____" rows every ~25 lines (page-estimated), Formatter aligns them. Less elegant; reliable.

### Future phases

- **Adversarial Reviewer**: at the very end of the pipeline (after Reviewer approval), an Adversarial Reviewer reads the lease as if it were the *tenant's lawyer*, looking for landlord-favourable terms that might be struck down. Useful for confidence; doubles the API cost. Phase 6+.
- **Live legal-knowledge feed**: rather than quarterly + event-driven YAML updates, a daily ingestion of SA Gazette + RHT decisions. Significant infrastructure; defer until there's clear demand.
- **Per-agency clause variants** (Tier D): when an agency wants their own standard "no smoking" wording, AgencyBranding + per-agency clause overrides. Admin UI.
- **Sales OTPs, mandates, supplier contracts**: same architecture; new Drafter persona + corpus. The Reviewer + Formatter are shared infrastructure.
- **Vault33 backing**: when Vault33's audit-trail + provenance maturity makes it worthwhile, migrate the corpus to Vault33. The MCP API stays stable; the backing store changes.

---

## 14. Glossary

- **RAG** — Retrieval-Augmented Generation. Pattern where an LLM is given relevant retrieved context (from a vector or keyed store) before generating, rather than relying on its training-time knowledge.
- **MCP** — Model Context Protocol. Anthropic's protocol for exposing tools / resources / prompts to LLMs via a standard interface. Lets the same RAG be consumed by Klikk's Django backend, Claude.ai, Cursor, future SaaS clients.
- **RHT** — Rental Housing Tribunal. Provincial bodies **established under RHA s7**; powers (investigation, mediation, binding rulings with effect of a Magistrate's Court order) are set out in **RHA s13**.
- **RHA** — Rental Housing Act 50/1999 (as amended by Act 35/2014). Primary SA residential rental statute.
- **CPA** — Consumer Protection Act 68/2008. Applies to fixed-term lease agreements as consumer contracts.
- **POPIA** — Protection of Personal Information Act 4/2013. Governs processing of tenant/landlord personal data.
- **PIE Act** — Prevention of Illegal Eviction from and Unlawful Occupation of Land Act 19/1998. Governs lawful eviction procedure.
- **STSMA** — Sectional Titles Schemes Management Act 8/2011. Governs body corporate and sectional title scheme management.
- **Signature token** — `⟪SIG#N⟫` opaque markers used inside the AI's view of the document to preserve signature blocks across edits (commit `a5c170df`).

---

## 15. Implementation kickoff

**Phase 0.5 starts here** (NOT Phase 1 — pre-implementation work first, per audit). The five gates that must pass before any Phase 1 LOC counts:

1. **Cache-hit spike confirms `cache_read_input_tokens > 0` from call #2.** ~50 LOC throwaway. If it doesn't hit, fix breakpoint structure (§6.6) before scaling up.
2. **Runtime decision locked + documented** (§10.2 + `docs/system/lease-ai-asgi-decision.md`). Option D: keep daphne, fix Caddy `flush_interval -1` on the v2 endpoint, `async def post`. Half a day; no framework migration.
3. **`LeaseAgentRunner` coordinator class lands first.** ~150 LOC. All agent dispatches go through it. Owns the 8-call cap, 90s wall-clock, 1-retry counter, cost cap, telemetry.
4. **`manage.py verify_caselaw_citations` lands BEFORE the first case-law YAML.** Pipeline gate against fabricated citations.
5. **`tool_choice: tool + strict: true + additionalProperties: false`** spiked against the `submit_audit_report` schema. Confirm the model snapshot supports it; confirm the schema dialect restrictions don't break the audit-report shape.

Once those 5 are green, Phase 1 begins: scaffold `backend/apps/leases/lease_law_corpus/` with the YAML loader + ChromaDB indexer (content-hash addressed, not on startup), then write 5 seed clauses to validate the round-trip end-to-end before scaling up to the full corpus.
