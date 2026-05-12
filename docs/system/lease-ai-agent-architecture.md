# Klikk Lease AI — Multi-Agent Architecture

| Field | Value |
|---|---|
| **Status** | Design locked, ready to build |
| **Phase** | 0 → 1 transition |
| **Date locked** | 2026-05-12 |
| **Author** | MC + Claude (design conversation) |
| **Implementation target** | `apps.leases.template_views` + new `apps.leases.lease_law_corpus` |
| **Endpoint** | `POST /api/v1/leases/templates/<id>/ai-chat-v2/` (parallel to v1 until cutover) |
| **Supersedes** | Single-agent `LeaseTemplateAIChatView` (kept as fallback during rollout) |

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
2. **AI assembles from "what's available" without checking applicability.** Claude pulls `tenant_2_*` / `tenant_3_*` merge fields because they're advertised, even when the user has one tenant.
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
| 6 | Corpus canonical form | **YAML files in `backend/apps/leases/lease_law_corpus/`**, synced to Chroma on startup |
| 7 | Corpus maintenance | **Code-only YAML + git PR** for v1; admin-UI deferred to Tier D |
| 8 | Indexing strategy | **Tags + citations + semantic** (all three on same chunks) |
| 9 | Query pattern | **Push for Drafter** (Front Door inlines clauses), **pull for Reviewer** (tool calls on demand) |
| 10 | Reviewer loop budget | **1 retry max** — worst case 4 LLM calls per request |
| 11 | Tool partitioning | **Strict** — each agent gets only tools matching its role |
| 12 | Question-asking UX | **Conversational** — agent asks in plain text, user answers in next message |
| 13 | Case-law sourcing | **AI-curated seed (Claude + MC review)** → staging/internal use → SA-lawyer review before external customer |
| 14 | Page layout | **Klikk-uniform for v1** — per-agency customisation deferred to Tier D |
| 15 | UX disclosure | **One coherent reply, pipeline visible in tools-used badges** — audit report in expander |
| 16 | API contract | **`POST /api/v1/leases/templates/<id>/ai-chat-v2/`** alongside v1 during rollout; v1 retired after stability |
| 17 | Streaming | **SSE within v2 from day one** — token streaming inside turns, status events between agents |

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
- `update_all(lines, summary)` (rare — for whole-doc rewrites; discouraged in prompt)
- `add_clause(after_line_index, clause_id, customise)` *(new — surgical insert from RAG by id)*
- `format_sa_standard(add_missing, preserve_custom)`
- `insert_signature_field(after_line_index, field_type, signer_role, field_name)`
- `highlight_fields(field_names, message)`
- `check_rha_compliance` (READ — runs the same diagnostic the Reviewer does, so Drafter can self-check before submitting; result returned to Drafter, not the user)

**Cannot do:** apply formatting, set page layout, set running headers. These are out of scope.

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
| Statute extracts | 30–50 sections | RHA full text, CPA s14 + s51, POPIA s11 / s14 / s23–25, PIE Act, STSMA |
| Case law decisions | 30–50 | Curated RHT decisions (Western Cape, Gauteng, KZN), grouped by topic |
| Pitfall patterns | ~50 | Abstracted lessons ("auto-renewal without CPA notice has been struck down") |

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
  text: |
    The deposit, totalling R{{ deposit }} ({{ deposit_words }}),
    will be held in an interest-bearing account with a registered
    financial institution. The interest accrued, less any reasonable
    account fees, accrues to the Tenant.
  merge_fields: [deposit, deposit_words]
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
- **Index built on Django startup:** YAML → ChromaDB collection `klikk_lease_law` + metadata table `LeaseLawChunk`
- **Embedding model:** `text-embedding-3-small` (cheap, fast, adequate for English legal text — chosen for cost; can upgrade)
- **Versioning:** every chunk has `version` + `effective_from`; index records `corpus_version` from the YAML directory's git SHA

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
│   7. Inline chunks into Drafter system prompt                  │
│   8. Dispatch to Drafter                                       │
└────────────────────────────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────────────────────────────┐
│  DRAFTER (LLM call 1)                                          │
│   • Reads pushed clauses + context + user message              │
│   • Calls tools: format_sa_standard / edit_lines / add_clause  │
│   • Multi-turn inside this agent if needed (max 4 turns)       │
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

Worst case: 5 LLM calls (4 in the loop + 1 if Drafter does 2 turns to handle a complex pushdown). Mostly: 3 calls.

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

- Backend: `StreamingHttpResponse` with `text/event-stream`
- Events:
  - `event: status` — `data: { phase, agent, message }`
  - `event: text_chunk` — `data: { agent, text }`
  - `event: tool_use` — `data: { agent, tool_name, input_summary }`
  - `event: document_update` — `data: { html, summary }`
  - `event: audit_report` — `data: { full critique JSON }`
  - `event: done` — `data: { reply, total_calls, total_latency_ms }`
  - `event: error` — `data: { message, recoverable }`
- Frontend: `fetch + ReadableStream` (not `EventSource` because we need to POST with auth headers + body)

### 10.3 Markdown in assistant replies

The assistant's text replies are rendered as Markdown (bold, lists, headings, code blocks, links) in the chat panel. Sanitized via DOMPurify before injection.

---

## 11. Phasing

| Phase | Scope | LOC est | Calendar |
|---|---|---|---|
| **0 — Design** | This document. Locks 17 architectural decisions. | 0 | done |
| **1 — Front Door + RAG infra** | New Django module `apps.leases.lease_law_corpus/`; YAML loader; ChromaDB indexer on startup; 4 query functions; `LeaseContext` dataclass; Front Door intent classifier (heuristic); clarifying-question return path. | ~400 | days |
| **2 — Drafter + Reviewer** | New `LeaseTemplateAIChatV2View`; Drafter system prompt + tool config; Reviewer system prompt + `submit_audit_report` tool; gate flow with 1-retry loop; `AILeaseAgentRun` model + persistence; SSE skeleton. | ~600 | days |
| **3 — Formatter** | Formatter system prompt; 4 new layout tools (`set_running_header`, `set_running_footer`, `set_per_page_initials`, `insert_page_break`); CSS `@page` infra in PDF render path; Gotenberg verification. | ~350 | days |
| **4 — Corpus seed** | 80–100 clauses + 30-50 statute extracts + 30-50 case law + ~50 pitfall patterns. Curated by Claude, reviewed by MC. | ~2000 lines YAML | week |
| **5 — Frontend** | New `LeaseTemplateAIChatPanelV2.vue` with SSE consumer, markdown rendering, audit-report expander, agent-aware tools-used badges, per-page status indicators. | ~600 | days |
| **6 — Cutover** | Feature flag enables v2 for selected templates; v1 fallback retained for 30 days; observe; cut over; retire v1. | ~50 | week |
| **7 — Extract to MCP product** | Move corpus + query API to a standalone MCP server `klikk-lease-law-rag`. Klikk calls it via MCP. Same kernel; new transport. Potentially the basis for a standalone product. | ~600 | weeks, when ready |

Estimated total Phase 1–6: **3–4 calendar weeks** of focused work, building on the foundation laid in commits `2795e47c` through `da13ed74` today.

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
- **Retry strategies on tool errors**: if a Drafter tool call fails (e.g. invalid line index), do we retry once with the error message in context, or abort? Lean toward retry once.

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
- **RHT** — Rental Housing Tribunal. Provincial bodies established by RHA s13 to resolve landlord-tenant disputes outside court.
- **RHA** — Rental Housing Act 50/1999 (as amended by Act 35/2014). Primary SA residential rental statute.
- **CPA** — Consumer Protection Act 68/2008. Applies to fixed-term lease agreements as consumer contracts.
- **POPIA** — Protection of Personal Information Act 4/2013. Governs processing of tenant/landlord personal data.
- **PIE Act** — Prevention of Illegal Eviction from and Unlawful Occupation of Land Act 19/1998. Governs lawful eviction procedure.
- **STSMA** — Sectional Titles Schemes Management Act 8/2011. Governs body corporate and sectional title scheme management.
- **Signature token** — `⟪SIG#N⟫` opaque markers used inside the AI's view of the document to preserve signature blocks across edits (commit `a5c170df`).

---

## 15. Implementation kickoff

Phase 1 starts here. Next concrete step: scaffold `backend/apps/leases/lease_law_corpus/` with the YAML loader + ChromaDB indexer, then write 5 seed clauses to validate the round-trip end-to-end before scaling up.
