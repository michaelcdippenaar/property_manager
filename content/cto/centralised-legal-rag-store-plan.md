# Centralised SA Legal Knowledge Base — Strategic Plan

| Field | Value |
|---|---|
| **Status** | Plan locked, ready for CEO sign-off and Phase A kickoff |
| **Owner** | CTO |
| **Date** | 2026-05-12 |
| **Supersedes** | Fragmented legal content in three skills + canonical citation map (which becomes the seed) |
| **Integrates with** | `docs/system/lease-ai-agent-architecture.md` decisions 3, 5, 6, 18, 19, 23 |
| **Seed input** | `content/cto/rha-citation-canonical-map.md` (HIGH/MEDIUM/LOW confidence per citation) |

---

## 1. TL;DR

Klikk's SA legal knowledge is fragmented across three skills, two design docs, a forthcoming RAG corpus, and (eventually) marketing copy + lease templates. Three skills already disagree on the same RHA s5(3) sub-section lettering — that is a POPIA s16 (information quality) failure mode at the company level, surfaced only because a second-pass auditor read the 1999 Gazette by hand. The fix is a single **canonical legal-fact store** — versioned YAML in `content/legal/`, lint-validated in CI, indexed into the existing lease-AI ChromaDB at deploy time, fronted by a stable Python query API (in v1) that becomes an MCP server (in v2). Skill `.md` files become **generated fan-out**, not curated truth. Lawyer review happens once per fact, not once per surface.

The five most important decisions I am locking:

1. **Canonical form is versioned YAML in `content/legal/`, not PostgreSQL, not ChromaDB.** Git is the audit trail. Diffs are reviewable. Branches are lawyer-review workflows. PostgreSQL caches the latest version for runtime lookups; ChromaDB indexes it for semantic retrieval. Both are downstream views, not sources of truth.
2. **The lease-AI Tier C corpus is subsumed entirely.** The lease AI does not maintain its own parallel statute YAML in `backend/apps/leases/lease_law_corpus/statutes/`. It maintains only clauses + case law + pitfalls; statute extracts come from the canonical legal store via the existing `query_statute` function (re-pointed). This preserves decisions 3, 5, 6 (corpus storage, MCP cutover) while removing the duplicate-truth problem.
3. **Skill `.md` files are generated, not edited.** `manage.py render_legal_skills` reads `content/legal/`, renders the three skills' reference markdown, and the rendered output is checked in for grep-ability. CI fails if the rendered files have drifted from the YAML. Authors stop writing skill files by hand; they write YAML.
4. **Lawyer attestation is a per-fact field, not a per-document signoff.** Each legal fact carries `verification_status`, `attested_by`, `attested_at`, `attestation_method`, and a `legal_provisional` flag. A lawyer reviews diffs of new/changed facts on a quarterly cadence (~30 mins per quarter once corpus is steady), not the whole corpus at every release.
5. **Phase 0 ships in 1 week, Phase A in 2-3 weeks, Phase B (MCP) deferred to lease-AI Phase 7.** No infrastructure beyond what Klikk already runs (PostgreSQL, Django, ChromaDB, git). Lawyer touchpoints minimised to: one initial sign-off on the seed, one quarterly review.

---

## 2. Why centralise — failure modes today

Today the same legal fact lives in three to five places. Each place was written by a different author at a different time with a different reading of the Act. Three concrete examples from `content/cto/rha-citation-canonical-map.md`:

**Failure A — RHT establishment section.** `klikk-leases-rental-agreement/references/sa-rental-law.md` cites RHA s13 as the section establishing the Rental Housing Tribunal. `klikk-legal-POPIA-RHA/references/06-rha-core-and-s5.md` and `07-rha-s4a-unfair-practices.md` both cite s7 (correct). The lease-AI design doc inherited s13 from the wrong skill. This is the canonical-citation-map row #1, HIGH confidence after audit. A customer reading the audit output from the lease AI would have seen "RHT established under s13" cited authoritatively — which is wrong on the face of the Act.

**Failure B — Deposit interest-bearing account sub-section.** All three skills agree on s5(3)(f). The 2026-04 audit, reading the 1999 Gazette directly, says s5(3)(d). Likely the 2014 amendment renumbered, but no one in the company can prove which letter is correct against the current consolidated Act without a lawyer. Today there is no single place to attest "we believe (f) is correct as of 2026-05-12, verified by Adv. X on date Y, version v3.1 of the canonical map" — so every surface that cites this fact is technically asserting a HIGH-stakes legal claim without an audit trail.

**Failure C — POPIA accuracy condition.** The lease-AI design doc cited POPIA s11(2) for the information-quality / accuracy condition. The standard reading (and the audit) say s16. SKILL-B (`06-rha-core-and-s5.md`) does not address it; the other skills are silent. There is nowhere in the codebase that says "POPIA s16 is the accuracy condition, here is the statute text, here is when we last verified it" — so the wrong cite propagates by copy-paste until an auditor catches it.

The pattern: **legal facts are written at the point of consumption, not at the point of truth.** When the law changes (or a lawyer corrects us), every consumer needs to be patched independently. Today they are not. This is exactly what POPIA s16 calls "reasonable steps to ensure complete, accurate, not misleading, updated where necessary" — and Klikk is not currently in a position to demonstrate those steps to the Information Regulator on demand.

A second, quieter failure mode: **the canonical citation map itself is in `content/cto/`, not in code or in any consumer's load path.** It exists as a single human-readable document but is not machine-consumable. A skill author cannot lint their `.md` file against it. The lease-AI Drafter cannot retrieve from it. It is a one-shot artefact, not a system. The plan below turns it into a system.

---

## 3. Architecture

**Recommendation: versioned YAML in `content/legal/` is the canonical store. PostgreSQL `legal_facts` is the runtime cache. ChromaDB (the lease-AI corpus index, decision 5) indexes a subset for semantic retrieval. All three coexist; only YAML is the source of truth.**

### The three layers

| Layer | Lives in | Owns | Mutability |
|---|---|---|---|
| **Canonical** | `content/legal/*.yaml` (git) | The facts themselves, lawyer attestation metadata, version history | Edit via PR only; PR is the lawyer-review workflow |
| **Runtime cache** | PostgreSQL table `legal_facts` (Django app `apps.legal_rag`) | Latest version of each fact, indexed for keyed lookup by `citation` or `concept_id` | Refreshed by `manage.py sync_legal_facts` on deploy (idempotent, version-aware) |
| **Semantic index** | ChromaDB collection `klikk_legal_v1` (in-app, lease-AI's existing infra per decision 5) | Embeddings + chunks for `query_*` semantic retrieval | Rebuilt by `manage.py reindex_legal_corpus` from PostgreSQL on `corpus_version` change |

### Why not the alternatives I considered

**Why not "single ChromaDB, no YAML, no Postgres"?** ChromaDB is an index, not a source of truth. There is no diff view. There is no PR. There is no human-readable history of "what did the law say in 2025-Q4 vs 2026-Q1". Lawyers cannot review a vector blob. A regulator cannot inspect a binary embedding. For a legal-fact store, this is disqualifying.

**Why not "single PostgreSQL JSONB, no YAML"?** Django migrations + raw DB rows are not a lawyer-review workflow. PRs are. A lawyer should be able to read a diff like "we changed RHA s5(3)(f) attestation from `mc_reviewed` to `lawyer_reviewed` on 2026-06-15 and updated the statute text from X to Y" — that needs to be in git, not in a database row. PostgreSQL is fine as the runtime read path, but not as the editorial workflow.

**Why not "MCP server fronting an external legal database (e.g. Jutastat / SAFLII)"?** Three reasons. (a) SAFLII is Cloudflare-protected and cannot be fetched programmatically from our environment — confirmed in the canonical map's preamble. (b) Vendor lock-in on legal IP we may sell later via Vault33's legal-fact layer. (c) Cost: per-query API pricing on legal databases is unpredictable; we want the worst-case bill to be $0/month for retrieval. We may *cite* SAFLII URLs from our records, but we do not depend on SAFLII at runtime.

**Why not "extend the lease-AI YAML corpus and call that the canonical store"?** Tempting, because decision 6 already commits to YAML in `backend/apps/leases/lease_law_corpus/`. But that location is wrong for two reasons. First, the corpus is owned by the leases app and indexed only when leases deploys — marketing copy that needs the same fact at website-build time should not depend on a Django app's deploy. Second, the lease-AI corpus is rightly scoped to **lease-AI** content (clauses, case law, pitfalls) — it should not absorb statute-of-the-law facts that other surfaces also consume. The right move is the **inverse**: the lease-AI corpus's `statutes/` directory **is removed**, and the lease-AI `query_statute` function reads from `content/legal/` via the runtime cache instead.

### Resulting directory layout

```
content/legal/                          # CANONICAL — the source of truth
├── README.md                           # Conventions, schema, workflow
├── CHANGELOG.md                        # Per-release human notes
├── _schema/
│   ├── legal_fact.schema.json          # JSON Schema for fact records
│   └── attestation.schema.json
├── statutes/
│   ├── rha/
│   │   ├── s5_3_a_parties.yaml         # one fact per file, by concept_id
│   │   ├── s5_3_f_deposit_interest.yaml
│   │   ├── s7_tribunal_establishment.yaml
│   │   └── ...
│   ├── popia/
│   ├── cpa/
│   ├── pie/
│   ├── stsma/
│   └── csos/
├── concepts/                           # Cross-statute concepts (e.g. "deposit refund timing")
│   ├── deposit_refund_timing.yaml
│   ├── lease_must_be_written.yaml
│   └── ...
├── case_law/                           # Migrated from lease-AI corpus
│   ├── western_cape/
│   ├── gauteng/
│   └── kzn/
├── pitfalls/                           # Migrated from lease-AI corpus
│   └── *.yaml
└── attestations/
    ├── 2026-Q2-attorney-review.yaml    # One file per attestation event
    └── ...

backend/apps/legal_rag/                 # NEW Django app — runtime cache + query API
├── models.py                           # LegalFact, LegalFactVersion, LegalAttestation, LegalCorpusVersion
├── management/commands/
│   ├── sync_legal_facts.py             # YAML → PostgreSQL (idempotent)
│   ├── reindex_legal_corpus.py         # PostgreSQL → ChromaDB
│   ├── verify_citations.py             # Lint corpus chunks + skills + design docs
│   └── render_legal_skills.py          # YAML → .md fan-out
├── queries.py                          # query_statute(), query_concept(), query_case_law(), list_pitfall_patterns()
├── signals.py                          # publish_fact, attest_fact signals
└── api/                                # Optional DRF surface (Phase B)

backend/apps/leases/lease_law_corpus/   # EXISTING — narrowed scope
├── clauses/                            # KEPT — lease-AI owns clause library
├── statutes/                           # REMOVED — read from content/legal/ instead
├── case_law/                           # MOVED to content/legal/case_law/
├── pitfall_patterns.yml                # MOVED to content/legal/pitfalls/
└── README.md                           # Cross-references content/legal/
```

This places the canonical store where it morally belongs — in `content/`, alongside `product/`, `brand/`, `sales/`, which `content/README.md` already designates as the bidirectional bridge. Marketing copy at website-build time reads from the same files the Django runtime reads from.

### Concurrency, drift, and the trust boundary

Two non-obvious mechanics make this work safely:

**Content-hash addressing.** Every YAML file's SHA256 is computed during `sync_legal_facts`. The `LegalFact` row stores the file hash; the `LegalCorpusVersion` row stores a Merkle-root-style hash of all files. On deploy, the runtime asserts `corpus_version == latest_index_version`. Mismatch → workers refuse to serve `query_*` endpoints with a 503 and a sev-1 alert. This is the same pattern the lease-AI architecture uses for its corpus (§6.3 of `docs/system/lease-ai-agent-architecture.md`), reused for consistency.

**Append-only attestation log.** `LegalAttestation` rows are insert-only. When a lawyer attests a fact, a row is written with the attorney's name, admission number, date, method (email PDF signed, in-person review, etc.), and the `legal_fact_version_id` they reviewed. Updating a fact creates a new `LegalFactVersion`; the new version starts at `verification_status='unattested'` until a new attestation row links to it. This is the audit trail a regulator asks for.

---

## 4. Schema

A legal fact has the following canonical shape. Example below is for the RHA s5(3)(f) interest-bearing-account requirement — the LOW-confidence row #11 from the canonical map.

```yaml
# content/legal/statutes/rha/s5_3_f_deposit_interest.yaml
---
concept_id: rha-s5-3-f-deposit-interest-bearing-account
type: statute_provision                  # statute_provision | case_law | pitfall | concept
version: 3
effective_from: 2014-08-01               # When the Act version this asserts about took effect
last_verified_at: 2026-05-12             # When we last checked the citation is still current
last_changed_at: 2026-05-12

# Citation grounding
statute: RHA
statute_full_title: "Rental Housing Act 50 of 1999, as amended by Act 35 of 2014"
section: "s5(3)(f)"
subsection_letter: "f"
parent_section: "s5(3)"
citation_string: "RHA s5(3)(f)"          # The canonical render
alternative_citations:                   # Historical / disputed renders, for the lint
  - source: "klikk-leases-rental-agreement/references/sa-rental-law.md"
    cite: "RHA s5(3)(f)"
    status: agrees
  - source: "klikk-legal-POPIA-RHA/references/06-rha-core-and-s5.md"
    cite: "RHA s5(3)(f)"
    status: agrees
  - source: "Opus auditor #2 of 1999 Gazette"
    cite: "RHA s5(3)(d)"
    status: disputes
    note: "Likely reading 1999 original numbering, not amended in-force text"

# The substance
statute_text: |
  The landlord must invest the deposit in an interest-bearing account
  with a financial institution and pay the tenant any interest accrued
  on the deposit, less any reasonable account fees, on the termination
  of the lease.
  [VERBATIM PENDING LAWYER VERIFICATION — bracketed text reconstructed from skill paraphrase]
statute_text_verbatim: false             # true only when lawyer has confirmed against gazette
statute_text_source: |
  Paraphrased from `klikk-legal-POPIA-RHA/references/06-rha-core-and-s5.md`
  and `klikk-rental-master/references/05-deposit-rules.md` (both 2026-04-17 vintage).
  Awaiting lawyer-supplied verbatim text from current consolidated Act.

plain_english_summary: |
  Any deposit the tenant pays must be held in an interest-bearing
  bank account. The interest belongs to the tenant (less reasonable
  bank fees), and must be paid to them when the lease ends.

# Confidence and provisional flagging (matches canonical map taxonomy)
citation_confidence: low                 # high | medium | low — per the canonical map
legal_provisional: true                  # If true, consumers must surface uncertainty to user
provisional_reason: |
  Three internal skills agree on (f); auditor reading 1999 Gazette
  says (d). Likely the 2014 amendment renumbered. Resolve via
  lawyer reading current consolidated Act.

# Lawyer attestation
verification_status: mc_reviewed          # ai_curated | mc_reviewed | lawyer_reviewed
attestation_id: null                     # FK to attestations/ file once attested
attested_by: null
attested_at: null
attestation_method: null                 # email_pdf_signed | in_person_review | counsel_opinion_letter

# Applicability — when consumers should retrieve this
applicability:
  property_types: [sectional_title, freehold, apartment, townhouse]
  tenant_counts: [any]
  lease_types: [fixed_term, month_to_month]
  jurisdictions: [za-national]

# Tags for retrieval (semantic + tag indexed)
topic_tags: [deposit, interest, refund, mandatory_clause]

# Cross-references
related_concepts:
  - rha-s5-3-h-deposit-refund-timing
  - rha-s5-3-k-joint-inspection
  - concept-deposit-refund-timing
related_clauses:
  - clause-deposit-interest-bearing-account-v1  # In lease-AI corpus, joined by id

# Sources we relied on (for the audit trail)
sources:
  - type: statute
    title: "Rental Housing Act 50 of 1999"
    url_archive: "https://www.gov.za/sites/default/files/gcis_document/201409/a50-99.pdf"
    accessed_at: 2026-05-12
    notes: "Original 1999 Gazette. Auditor #2 read this version."
  - type: skill
    path: ".claude/skills/klikk-legal-POPIA-RHA/references/06-rha-core-and-s5.md"
    accessed_at: 2026-05-12
  - type: canonical_map
    path: "content/cto/rha-citation-canonical-map.md"
    row: 11
    confidence: low

# Penalties / consequences of non-compliance (for marketing copy + lease audit)
non_compliance:
  - actor: landlord
    consequence: "Tribunal may order landlord to pay interest at prevailing rate"
    cited_via: RHA s13 (Tribunal powers)
  - actor: landlord
    consequence: "Treated as unfair practice under RHA s4A"

# Disclaimers consumers must render
disclaimers:
  - "Not legal advice. Verify with admitted attorney before reliance."
  - "Sub-section letter provisional pending current-consolidated-Act verification."
```

### Schema invariants enforced by JSON Schema + lint

- `concept_id` is globally unique, kebab-case, max 80 chars.
- `citation_string` matches `^(RHA|POPIA|CPA|PIE|STSMA|CSOS) s\d+(\(\d+\))?(\([a-z]\))?$` for statutes.
- `verification_status: lawyer_reviewed` requires `attestation_id` non-null, `attested_by` non-null, `attested_at` non-null.
- `legal_provisional: true` requires `citation_confidence` in `{medium, low}` and `provisional_reason` non-empty.
- `statute_text_verbatim: true` requires `verification_status: lawyer_reviewed`. You cannot claim verbatim statute text without lawyer attestation.
- `effective_from` is ISO 8601 date.
- `sources` list is non-empty; at least one source has `type: statute` for a `type: statute_provision` fact.
- Cross-references resolve (`related_concepts` ids must exist).

The schema is `content/legal/_schema/legal_fact.schema.json`. `manage.py verify_citations` runs the schema check + cross-reference resolution + alternative-citation lint in CI.

### Attestation record shape

```yaml
# content/legal/attestations/2026-Q2-attorney-review.yaml
---
attestation_id: 2026-Q2-attorney-review
attorney_name: "Adv. Jane Doe SC"
attorney_admission_number: "LPC-WC-12345"
attorney_firm: "Doe Attorneys, Stellenbosch"
attestation_method: counsel_opinion_letter
attestation_date: 2026-06-15
opinion_letter_pdf_sha256: "ab12cd34ef56..."
opinion_letter_storage: "vault33://klikk-internal/legal-attestations/2026-Q2.pdf"

facts_attested:
  - concept_id: rha-s5-3-f-deposit-interest-bearing-account
    fact_version: 3
    finding: confirmed                   # confirmed | corrected | rejected
  - concept_id: rha-s5-3-h-deposit-refund-timing
    fact_version: 2
    finding: corrected
    correction_summary: |
      Confirmed sub-section letter is (h). Statute text amended from
      "within reasonable time" to verbatim "within 14 days of expiration
      of the lease". Updated statute_text_verbatim: true.
  - concept_id: rha-s7-tribunal-establishment
    fact_version: 1
    finding: confirmed

scope: |
  Per-fact review of RHA s5 sub-sections (f), (h), (k), (m) and the
  s7/s13 distinction, against the current consolidated Rental Housing
  Act 50 of 1999 as in force at 2026-06-15.

cost_zar: 4500
```

Attestations are append-only. A correction creates a new fact version + a new attestation entry; the old version remains queryable for any document signed under it.

---

## 5. Citation grounding & lawyer-review workflow

### The lifecycle of a legal fact

```
[draft]
  │ Claude proposes a fact (concept_id, citation, plain_english_summary)
  │ Written to content/legal/statutes/... with verification_status: ai_curated
  ▼
[ai_curated]
  │ MC reviews diff in PR; merges if reasonable
  ▼
[mc_reviewed]
  │ verification_status: mc_reviewed
  │ Usable by Drafter (with legal_provisional flag if citation_confidence ∈ {medium, low})
  │ NOT usable in externally-facing marketing copy without disclaimers
  ▼
  │ Lawyer reviews quarterly diff of all new mc_reviewed facts
  │ Opinion letter received → attestation YAML added
  ▼
[lawyer_reviewed]
  │ verification_status: lawyer_reviewed
  │ legal_provisional: false (if attestation finding=confirmed)
  │ Usable everywhere, including externally-facing claims
```

### Who attests and how often

- **Lawyer:** SA-admitted attorney with rental-housing practice. MC's first hire here should be the attorney already advising on the FICA pipeline (so we don't onboard two firms). Target: Stellenbosch or Cape Town firm, fixed monthly retainer or quarterly fixed-fee opinion letter.
- **Cadence:** **quarterly batched review** by default. Out-of-band review on (a) law changes (Gazette amendment lands), (b) Tribunal precedent we want to cite, (c) any LOW-confidence row in the canonical map being asked about by a customer or sales channel.
- **Scope per quarter:** every fact with `verification_status: mc_reviewed` and `last_changed_at` since the previous attestation. A steady-state corpus changes maybe 5-20 facts per quarter — that is a 30-minute review for an attorney. Their opinion letter references each `concept_id` + `fact_version` explicitly.
- **Cost ceiling:** approximate quarterly review fee ~R3000-R6000 fixed-fee. Across a year, R12k-R24k. Compared to the cost of one POPIA s16 action by the Information Regulator (R10m fine ceiling), this is insurance.

### Audit trail visible to the Information Regulator

When (not if) a regulator or aggrieved tenant asks "on what basis did Klikk publish this legal claim", we produce:

1. `git log content/legal/statutes/rha/s5_3_f_deposit_interest.yaml` — every change with author, date, message.
2. The fact's `verification_status` at the time the claim was published, via `LegalFactVersion` rows joined on `created_at`.
3. The `LegalAttestation` row pointing to the opinion letter PDF (hash + storage URI), signed by an admitted attorney.
4. The `AILeaseAgentRun.corpus_version` on the lease that was generated — proving which version of the corpus was applied.
5. The disclaimers rendered to the user, from `disclaimers` field on each fact at retrieval time.

This is the "reasonable steps" defence under POPIA s16. We are not asserting the law is right — we are asserting we took reasonable steps to verify, and we can show our work.

### POPIA s17/18 openness — what the data subject sees

A tenant whose lease was generated by the lease AI sees, in the audit-report expander already designed in §10.1 of the lease-AI doc, a per-finding citation with a `confidence_level` chip. The chip resolves to the `verification_status` of the underlying fact at the time of generation. `lawyer_reviewed` chips are green; `mc_reviewed` are amber with a "verified by Klikk against current statute" tooltip; `ai_curated` is grey with "AI-curated; not lawyer-reviewed". This is openness in the operational sense — the data subject can see the strength of the legal claim, not just the claim itself.

---

## 6. Read API for downstream consumers

The query API is the **stable surface** that every consumer calls. The implementation may change (Python imports in v1, MCP tools in v2, gRPC in v3 if we ever need it); the signatures do not.

### v1 signatures — Python functions in `apps.legal_rag.queries`

```python
# backend/apps/legal_rag/queries.py

def query_statute(citation: str, *, at_date: date | None = None) -> LegalFact:
    """
    Look up a statute provision by canonical citation string.
    Returns the latest version effective at `at_date` (defaults to today).
    Raises LegalFactNotFound if the citation is not in the corpus.

    Example:
        fact = query_statute("RHA s5(3)(f)")
        fact.plain_english_summary
        fact.citation_confidence   # "low"
        fact.legal_provisional     # True
        fact.disclaimers           # ["Not legal advice.", "Sub-section letter provisional..."]
    """

def query_concept(concept_id: str, *, at_date: date | None = None) -> LegalFact: ...

def query_facts_by_topic(
    topic_tags: list[str],
    *,
    statute: str | None = None,
    min_confidence: Literal["high", "medium", "low"] = "medium",
    include_provisional: bool = False,
    k: int = 10,
) -> list[LegalFact]:
    """
    Tag-and-filter retrieval. Used by the lease-AI Drafter to pull
    "all the deposit-related facts for a sectional-title lease".
    """

def query_semantic(
    natural_query: str,
    *,
    fact_types: list[Literal["statute_provision", "case_law", "pitfall", "concept"]] | None = None,
    min_confidence: Literal["high", "medium", "low"] = "medium",
    k: int = 10,
) -> list[LegalFact]:
    """
    Embedding-similarity retrieval via ChromaDB. Used by the lease-AI
    Reviewer when it doesn't know which citation to look up.
    """

def query_case_law(
    topic_tags: list[str] | None = None,
    jurisdiction: str | None = None,
    since_year: int | None = None,
    natural_query: str | None = None,
    k: int = 10,
) -> list[LegalFact]: ...

def list_pitfall_patterns(
    topic_tags: list[str] | None = None,
) -> list[LegalFact]: ...

def list_facts_at_version(corpus_version: str) -> list[LegalFact]:
    """
    Snapshot view. Used by audit log when reconstructing 'what did
    the corpus look like when this lease was generated'.
    """
```

Every return value carries `corpus_version`, `fact_version`, `verification_status`, and `disclaimers`. Consumers must pass `disclaimers` through to the user-facing surface — there is no way to render a fact without its disclaimers attached.

### Consumer usage examples

**Lease-AI Drafter (push pattern, decision 9 of lease-AI doc):**

```python
# In Front Door, before dispatching to Drafter
clauses = lease_corpus.query_clauses(topic_tags=["deposit"], property_type="sectional_title", k=10)
statutes = legal_rag.query_facts_by_topic(
    topic_tags=["deposit"],
    statute="RHA",
    min_confidence="medium",
    include_provisional=False,
    k=10,
)
rag_block = build_rag_block(clauses, statutes)   # Inlined into Drafter system prompt
# Drafter assembles clauses; cites the statute provisions
```

**Lease-AI Reviewer (pull pattern):**

```python
# Reviewer's tool definition
{
    "name": "query_statute",
    "description": "Look up the statute text and verification status for a given RHA / POPIA / CPA / PIE / STSMA / CSOS citation. Returns plain_english_summary, statute_text, citation_confidence, legal_provisional, disclaimers.",
    "input_schema": { ... }
}
```

**Marketing copywriter (Astro build time):**

```ts
// content/website/copy/compliance-page.astro
import { queryFact } from "@klikk/legal-rag-client";

const depositFact = await queryFact("rha-s5-3-f-deposit-interest-bearing-account");

if (depositFact.verification_status !== "lawyer_reviewed") {
  throw new Error(`Marketing copy depends on ${depositFact.concept_id} which is not lawyer-reviewed.`);
}
// Render plain_english_summary + disclaimers
```

The Astro client at build time hits a small Django JSON endpoint `/api/v1/legal-rag/facts/<concept_id>/` (auth: API key, scope: read-public-lawyer-reviewed-only) so the website never deploys with an `ai_curated` claim by accident. CI fails the website build if the endpoint returns a non-`lawyer_reviewed` fact.

**Skill `.md` render (build time, Phase A):**

```bash
$ manage.py render_legal_skills
✓ Rendered .claude/skills/klikk-legal-POPIA-RHA/references/06-rha-core-and-s5.md (37 facts, all sources from content/legal/)
✓ Rendered .claude/skills/klikk-rental-master/references/05-deposit-rules.md (12 facts)
✓ Rendered .claude/skills/klikk-leases-rental-agreement/references/sa-rental-law.md (28 facts)
✓ No drift. Skills synced to corpus_version=cd341a8b9f12.
```

### Response shape — what a consumer gets back

```python
@dataclass
class LegalFact:
    concept_id: str
    type: Literal["statute_provision", "case_law", "pitfall", "concept"]
    citation_string: str
    plain_english_summary: str
    statute_text: str | None
    statute_text_verbatim: bool
    citation_confidence: Literal["high", "medium", "low"]
    legal_provisional: bool
    provisional_reason: str | None
    verification_status: Literal["ai_curated", "mc_reviewed", "lawyer_reviewed"]
    attested_by: str | None
    attested_at: date | None
    applicability: ApplicabilityRules
    topic_tags: list[str]
    related_concepts: list[str]
    sources: list[Source]
    disclaimers: list[str]
    fact_version: int
    corpus_version: str
    effective_from: date
    last_verified_at: date
```

This is the contract. The query API will never return a fact without these fields populated.

---

## 7. Skill fan-out / generation strategy

**Recommendation: skill `.md` files are generated from `content/legal/` at build time, checked in, lint-validated against the YAML. Authors edit YAML; skills are downstream views.**

### Why not "auto-generate at agent load time"

Tempting but wrong. Three reasons:

1. **Grep-ability.** Engineers and the autopilot read `.md` files with `Read`/`Grep` constantly. If they are only generated at agent invocation, you cannot grep the repo for "what does this skill say about deposits". `.md` files must remain on disk.
2. **Skill loading semantics.** Claude Code loads skill `references/*.md` lazily, not eagerly. Adding a "generate-on-load" step adds latency and a failure mode that takes down the agent if generation breaks.
3. **Provenance.** A skill file in git history is a record of "what the agent was told at this commit". Generating at load time hides that history.

### Why not "manually curated, lint-validated against YAML"

Also tempting; this is what we'd have if we just kept editing `.md` and added a CI check. Two reasons against:

1. **Editorial duplication.** Every fact edit happens twice — once in YAML, once in the `.md`. Eventually they drift. The whole point of centralisation is single-edit.
2. **Lawyer can't review three surfaces.** When the attorney signs off on RHA s5(3)(f), they sign off on one fact. They should not also have to read three `.md` files to confirm the rendered text is correct. Generated output is deterministic; CI proves the `.md` matches the YAML.

### How generation works

`manage.py render_legal_skills` produces one `.md` per skill reference file by reading a small Jinja2 template per file. The template includes the YAML facts inline with their `plain_english_summary`, `citation_string`, `citation_confidence`, and a footer that lists `corpus_version` + `last_verified_at`. Example:

```
backend/apps/legal_rag/skill_templates/
├── klikk-legal-POPIA-RHA/
│   ├── 01-popia-core.md.j2
│   ├── 06-rha-core-and-s5.md.j2
│   └── ...
├── klikk-rental-master/
│   └── ...
└── klikk-leases-rental-agreement/
    └── ...
```

A template looks like (excerpt):

```jinja2
# RHA Core: Section 5 — Lease Agreement Requirements

> Source: `content/legal/` (corpus_version: {{ corpus_version }}, generated {{ now() }})
> Do not edit this file directly. Edit YAML in `content/legal/statutes/rha/` and run `manage.py render_legal_skills`.

## Lease must be written
- **Citation:** {{ fact("rha-s5-2-right-to-written-lease").citation_string }}
- **Confidence:** {{ fact("rha-s5-2-right-to-written-lease").citation_confidence }}
- **Summary:** {{ fact("rha-s5-2-right-to-written-lease").plain_english_summary }}

## Mandatory lease contents
{% for fact_id in concept("rha-s5-3-mandatory-contents").related_concepts %}
### {{ fact(fact_id).citation_string }}
{{ fact(fact_id).plain_english_summary }}
{% if fact(fact_id).legal_provisional %}
> **Provisional:** {{ fact(fact_id).provisional_reason }}
{% endif %}
{% endfor %}
```

`manage.py verify_citations --strict` runs in CI on every PR. It re-renders the skills and `git diff`s against checked-in. Any diff = CI fail. Authors who change a skill `.md` directly will be told "edit the YAML and re-render".

### Skills that are NOT generated

Some skill content is methodology / workflow / process, not legal facts (e.g. `klikk-rental-master/references/01-rental-workflow.md` is mostly process flow). Those stay hand-written. Only **the legal-fact sections** of each skill are generated. The render command operates on tagged sections within each `.md`:

```markdown
<!-- BEGIN AUTO-GENERATED legal-facts -->
... generated content ...
<!-- END AUTO-GENERATED legal-facts -->
```

Anything outside the markers is preserved across renders.

### Skill index — what gets generated vs hand-written

| Skill | File | Generation mode |
|---|---|---|
| `klikk-legal-POPIA-RHA` | `01-popia-core.md` | Fully generated (legal facts) |
| `klikk-legal-POPIA-RHA` | `02-popia-special-pi.md` | Fully generated |
| `klikk-legal-POPIA-RHA` | `03-popia-direct-marketing.md` | Fully generated |
| `klikk-legal-POPIA-RHA` | `04-popia-cross-border.md` | Fully generated |
| `klikk-legal-POPIA-RHA` | `05-paia-manual-and-dsar.md` | Fully generated |
| `klikk-legal-POPIA-RHA` | `06-rha-core-and-s5.md` | Fully generated |
| `klikk-legal-POPIA-RHA` | `07-rha-s4a-unfair-practices.md` | Fully generated |
| `klikk-legal-POPIA-RHA` | `08-interplay-fica-nca-cpa-ecta.md` | Fully generated |
| `klikk-legal-POPIA-RHA` | `09-tenant-pi-protected.md` | Fully generated |
| `klikk-legal-POPIA-RHA` | `10-compliance-documents.md` | Fully generated |
| `klikk-legal-POPIA-RHA` | `11-penalties-enforcement.md` | Fully generated |
| `klikk-rental-master` | `01-rental-workflow.md` | Hand-written (process) |
| `klikk-rental-master` | `02-parties-and-roles.md` | Hand-written |
| `klikk-rental-master` | `03-documents-and-records.md` | Hand-written |
| `klikk-rental-master` | `04-legislation-overview.md` | **Mixed** — legal sections generated, narrative hand-written |
| `klikk-rental-master` | `05-deposit-rules.md` | Mixed |
| `klikk-rental-master` | `06-eviction-and-pie-act.md` | Mixed |
| `klikk-rental-master` | `07-rental-income-tax.md` | Hand-written |
| `klikk-rental-master` | `08-utilities-and-municipal.md` | Hand-written |
| `klikk-rental-master` | `09-body-corporate-sectional-title.md` | Mixed |
| `klikk-rental-master` | `10-common-addendums.md` | Mixed |
| `klikk-rental-master` | `11-roles-and-permissions.md` | Hand-written |
| `klikk-leases-rental-agreement` | `agreement-structure.md` | Hand-written (process) |
| `klikk-leases-rental-agreement` | `sa-rental-law.md` | **Fully regenerated** (currently the worst offender — swaps s5(3)(c)/(d), wrong Tribunal cite) |

---

## 8. Migration plan

Concrete steps from today's fragmented state to centralised state. Eight gates; each is reviewable on its own.

### Step 1 — Lock the canonical citation map as the authoritative seed (day 1)

The canonical citation map (`content/cto/rha-citation-canonical-map.md`) is already the authoritative seed for high-stakes citations. It does not move; it becomes the input to the YAML generator. Run a one-time script `tools/seed_legal_corpus_from_map.py` that reads the map and emits stub YAML files for every row, populated with `verification_status: mc_reviewed` (HIGH rows) or `mc_reviewed` + `legal_provisional: true` (MEDIUM/LOW rows). Output: ~50 YAML files in `content/legal/statutes/`.

### Step 2 — Scaffold the `legal_rag` Django app (day 1-2)

- `python manage.py startapp legal_rag` in `backend/apps/legal_rag/`.
- Add to `INSTALLED_APPS`.
- Migrations: `LegalFact`, `LegalFactVersion`, `LegalAttestation`, `LegalCorpusVersion`.
- Empty `queries.py`, `signals.py`.
- One Django check that `content/legal/` is parseable and valid against `_schema/legal_fact.schema.json`.

### Step 3 — Build the loader + Postgres sync (day 2-3)

`manage.py sync_legal_facts` reads YAML → upserts `LegalFact` rows → emits `publish_fact` signal. Idempotent. Acquires `pg_advisory_lock('legal_facts_sync')` to prevent concurrent runs.

### Step 4 — Build the verifier + skill renderer (day 3-5)

`manage.py verify_citations` does: (a) schema check on every YAML, (b) cross-reference resolution, (c) alternative-citation lint (every cite in lease-AI design doc, skills, marketing copy must resolve to a fact in `content/legal/`), (d) re-render skill `.md` and diff. CI gate.

`manage.py render_legal_skills` re-renders the three skill directories' generated sections.

### Step 5 — Migrate skill content into YAML (day 5-7)

For each existing `.md` file, extract every legal-fact assertion → write to a YAML file (or merge into an existing one) → re-render the `.md` → diff is empty. Use the canonical map as the arbitrator on any contradiction.

**Order of operations:**

1. `klikk-leases-rental-agreement/references/sa-rental-law.md` — the worst offender; regenerate fully from canonical map.
2. `klikk-rental-master/references/05-deposit-rules.md` — update three `s5(3)(f)` references to canonical.
3. `klikk-legal-POPIA-RHA/references/06-rha-core-and-s5.md` — bring in line with canonical.
4. `klikk-legal-POPIA-RHA/references/07-rha-s4a-unfair-practices.md` — verify only; mostly already aligned.
5. All other POPIA / RHA / CPA / PIE references — extract into YAML batch.

### Step 6 — Subsume the lease-AI statute corpus (day 7-9)

`backend/apps/leases/lease_law_corpus/statutes/` becomes empty (or removed). The Drafter's `query_statute` tool is rewired to call `apps.legal_rag.queries.query_statute()`. The lease-AI indexer (`manage.py reindex_lease_corpus`) reads from `content/legal/statutes/` for statute chunks AND from `backend/apps/leases/lease_law_corpus/clauses/` for clause chunks — the two corpora coexist in the same ChromaDB collection but live in different YAML roots.

Case law and pitfall patterns migrate too: `backend/apps/leases/lease_law_corpus/case_law/` → `content/legal/case_law/`; `pitfall_patterns.yml` → `content/legal/pitfalls/`. The lease-AI's `query_case_law` and `list_pitfall_patterns` re-point to `apps.legal_rag.queries`.

The lease-AI design doc (`docs/system/lease-ai-agent-architecture.md`) is updated in §6.1 / §6.3 to reflect: "Statute extracts, case law, and pitfall patterns are owned by `apps.legal_rag` and live in `content/legal/`. The lease-AI corpus owns clauses only."

### Step 7 — First lawyer attestation (week 2-3)

Package the canonical citation map + the current YAML state + the list of LOW-confidence rows requiring sub-section verification → send to retained attorney → receive opinion letter → write `content/legal/attestations/2026-Q2-attorney-review.yaml` → flip `verification_status: lawyer_reviewed` on confirmed facts → run `manage.py sync_legal_facts` → first lawyer-reviewed corpus version is live.

### Step 8 — CI lint becomes blocking (week 3)

`manage.py verify_citations --strict` is added to CI. Any new statute citation in any `.md`, `.yml`, `.py`, `.vue`, `.astro`, `.ts` file that does not resolve to a fact in `content/legal/` fails CI. From this point forward, you cannot land a legal claim without it being centralised first.

### What gets deprecated, what gets canonical, who reviews

| Artifact | After migration | Reviewer |
|---|---|---|
| `content/cto/rha-citation-canonical-map.md` | **Kept as historical record** + reference for the LOW-confidence rows pending lawyer review; eventually superseded by attestation YAMLs | CTO |
| `.claude/skills/klikk-legal-POPIA-RHA/references/*.md` | **Generated** from YAML | CI |
| `.claude/skills/klikk-rental-master/references/*.md` | **Mixed** — legal sections generated, process sections hand-written | CTO + author |
| `.claude/skills/klikk-leases-rental-agreement/references/sa-rental-law.md` | **Fully regenerated** | CI |
| `.claude/skills/klikk-leases-rental-agreement/references/agreement-structure.md` | **Hand-written** (process) | Author |
| `backend/apps/leases/lease_law_corpus/statutes/` | **Removed** — superseded by `content/legal/statutes/` | CTO |
| `backend/apps/leases/lease_law_corpus/case_law/` | **Moved** to `content/legal/case_law/` | CTO |
| `backend/apps/leases/lease_law_corpus/pitfall_patterns.yml` | **Moved** to `content/legal/pitfalls/` | CTO |
| `backend/apps/leases/lease_law_corpus/clauses/` | **Kept** — lease-AI clause library, scoped correctly | Lease-AI team |
| `docs/system/lease-ai-agent-architecture.md` §6 | **Updated** to reflect new corpus boundary | CTO |

---

## 9. MCP server exposure (Phase 2 / lease-AI Phase 7)

When the legal-fact store becomes valuable to expose externally (or to other Klikk products beyond lease-AI), it carves out as a standalone MCP server. This aligns with lease-AI architecture decision 5 (Phase 7 extraction) and converges the two extractions into one server.

### API surface — Resources vs Tools

**MCP Resources** (read-only, content-addressable, cacheable):

- `legal://facts/{concept_id}` — single fact by id
- `legal://facts/by-citation/{citation_string}` — single fact by canonical citation
- `legal://facts/by-tag/{topic_tag}` — list of facts for a tag
- `legal://attestations/{attestation_id}` — full attestation record
- `legal://corpus/version/{corpus_version}` — manifest of all facts at a version
- `legal://corpus/changelog` — human-readable changelog

**MCP Tools** (active queries, may invoke embedding model):

- `query_statute(citation, at_date?)` → LegalFact
- `query_facts_by_topic(topic_tags, statute?, min_confidence?, k?)` → list[LegalFact]
- `query_semantic(natural_query, fact_types?, min_confidence?, k?)` → list[LegalFact]
- `query_case_law(topic_tags?, jurisdiction?, since_year?, natural_query?, k?)` → list[LegalFact]
- `list_pitfall_patterns(topic_tags?)` → list[LegalFact]
- `cite_verify(citation_string)` → boolean + suggested correction (lint for external consumers)

Resources are preferred for stable lookups (cached, deterministic, indexable). Tools are for parameterised queries.

### Authentication & cross-tenant isolation

- **Internal Klikk consumers** (Django backend, Astro website build) use API-key authentication with a service account. No multi-tenancy concern — internal services see the full corpus.
- **External consumers** (if/when productised): JWT-scoped clients with a `tier` claim:
  - `tier: public` — only `lawyer_reviewed` facts; only `min_confidence: high`; no statute_text_verbatim unless attested; rate-limited to 1000 req/day.
  - `tier: customer` — paying SaaS customer; full corpus including `mc_reviewed`; statute_text_verbatim included; rate-limited to 100k req/day.
  - `tier: partner` — Vault33-integrated; same as customer plus webhook on corpus version changes.
- **Cross-tenant isolation:** none needed — the corpus is the same for every consumer. Customisation per-tenant (e.g. "show me only Western Cape case law") is a query parameter, not a tenant-scoped data set.
- **POPIA-residency:** the MCP server runs in `af-south-1` (Cape Town AWS region) or on-prem in Stellenbosch. No customer PI flows through it — it serves only public-record legal facts.

### Pricing model (if productised)

This is the same kernel Vault33 would expose if it ever sells its legal-fact layer. Not for v1, but the architecture supports it:

- **Free tier:** 100 reqs/day, `lawyer_reviewed` only, public statutes only, attribution required.
- **Standard:** R499/month, 10k reqs/day, full corpus, no attribution.
- **Pro:** R2999/month, 100k reqs/day, webhook on corpus changes, custom topic tags.
- **Enterprise:** custom — on-prem deployment, custom attestation cadence, opinion-letter access.

Not a Phase A concern. Designed for it; not built for it.

### Latency budget for MCP cutover

Direct Python imports add ~0ms. MCP-over-HTTP adds 50-200ms per query, plus serialisation overhead. Per the lease-AI doc's audit J (§13), this is acceptable for the lease AI but should be measured. Recommendation: stay in-process for v1; switch to MCP only when (a) a second Klikk product wants the corpus (Real Estate, BI), or (b) we sell to first external customer.

---

## 10. POPIA & legal-liability handling

### POPIA accuracy condition (s16) — the bar we must clear

POPIA s16 requires that personal information be "complete, accurate, not misleading and updated where necessary". The corpus stores **public legal facts**, not personal information — so s16 doesn't directly apply to the corpus content itself. But it applies in two indirect ways:

1. **When the lease AI tells a tenant "your deposit must be in an interest-bearing account", that statement is *about* the tenant's relationship with their landlord — adjacent to personal information.** If the cite is wrong (s5(3)(d) vs s5(3)(f), or worse), the tenant relies on a misleading statement. We can be argued into s16 territory.
2. **When marketing copy says "Klikk's lease audit checks compliance with RHA s5(3)(f)" and the cite is wrong, that is a misrepresentation under the CPA and a potential s16 violation indirectly because it sells to data subjects on inaccurate premises.**

The central store + lawyer attestation gives us a defensible answer: "we centralised our legal-fact sources, lawyer-attested them quarterly, lint-validated them in CI, and version-stamped every customer-facing artefact with the corpus version it was generated against. Reasonable steps."

### POPIA s17/18 openness — what data subjects see

Every consumer of the corpus must surface the fact's `disclaimers` and `verification_status` to the data subject. Concretely:

- The lease-AI audit-report expander shows the `verification_status` chip per finding.
- Marketing copy that depends on a fact renders the `disclaimers` in fine print at the bottom of the page.
- The lease PDF includes a footer: "Generated by Klikk lease-AI v2 against legal corpus version `{corpus_version}` on `{date}`. This is not legal advice."

### Per-customer audit trail — proving "the lease was generated against this version"

Already baked in via the lease-AI design doc (§6.3): every `AILeaseAgentRun` records the `corpus_version`. When a tenant sues five years later claiming the deposit clause was wrong, we run `list_facts_at_version(corpus_version)` and show: "at the time your lease was signed, the corpus said X, attested by Adv. Doe on date Y." If the law has changed since, that is mitigation, not liability.

### Disclaimers — what we render and where

Three layers, in order of strength:

1. **Per-fact disclaimers** (in YAML, attached to each retrieval): "Not legal advice. Sub-section letter provisional pending current-consolidated-Act verification."
2. **Per-document disclaimer** (in lease PDF footer + audit expander): "Generated by Klikk lease-AI against legal corpus `{corpus_version}` on `{date}`. Not legal advice. Verify with admitted attorney before reliance."
3. **Per-surface disclaimer** (marketing site footer, in-product Help): "Klikk provides software that surfaces South African rental law in an AI-assisted way. We are not a law firm. Information is current as of `{last_verified_at}` but is not a substitute for legal counsel."

### Lawyer sign-off cadence — what triggers a review

| Trigger | Cadence | Scope |
|---|---|---|
| Initial seed attestation | One-off, week 2-3 of Phase A | All `mc_reviewed` facts |
| Steady-state quarterly review | Q1, Q2, Q3, Q4 | Any fact with `last_changed_at` since last attestation |
| Law change (Gazette amendment) | Within 14 days of Gazette publication | Affected facts only; opinion letter + immediate corpus patch |
| New customer-facing claim | Within sprint, before launch | The specific facts the claim depends on |
| Information Regulator inquiry | Within 5 business days | Whatever the IR asks about |
| Tenant lawsuit alleging citation error | Immediate, opinion-letter priority | The specific fact in dispute |

Steady-state cost: ~R20k/year. Crisis cost: variable but capped by retainer terms in the attorney's engagement letter. MC's call to set the retainer.

### Versioning so we can prove what we said when

The audit trail is:

```
lease.id → AILeaseAgentRun.corpus_version → LegalCorpusVersion.merkle_hash
  → LegalFactVersion[N] (each fact at that version)
    → LegalAttestation (linked by attestation_id)
      → opinion_letter_pdf_sha256 + opinion_letter_storage URI (Vault33 stored, encrypted at rest)
```

A regulator or court receives: "On 2026-06-15, lease #12345 was generated against corpus `cd341a8b9f12`. Fact `rha-s5-3-f-deposit-interest-bearing-account` at version 3 was the basis for the deposit clause. That version was attested by Adv. Jane Doe SC (LPC-WC-12345) on 2026-06-15 via opinion letter (PDF hash `ab12...`, retrievable from Vault33 internal storage). Here is the opinion letter."

That is the audit trail. It exists today only in scattered Markdown files. The central store makes it queryable.

---

## 11. Tech stack recommendation

Specific picks, justified.

| Concern | Pick | Why |
|---|---|---|
| **Canonical store format** | YAML (1.2, safe-load) | Diffable, human-readable, supports multi-line `\|` for statute text, library support universal. Not JSON (no comments), not TOML (no multi-line strings). |
| **Schema validation** | `jsonschema` (PyPI) against `_schema/legal_fact.schema.json` | Already used in `backend/apps/leases/`. Familiar. Supports JSON Schema 2020-12. |
| **Runtime cache** | PostgreSQL 15 + Django 5 ORM | Already in production. `JSONField` for the fact body; promoted columns for indexed fields (`citation_string`, `concept_id`, `verification_status`, `corpus_version`). |
| **Semantic index** | ChromaDB-in-app (same instance as lease-AI corpus, decision 5) | Reuse existing infra. One collection `klikk_legal_v1`. Separate collection from lease-AI clauses to avoid mixing types. |
| **Embeddings** | `text-embedding-3-small` (OpenAI) — same as lease-AI corpus | Cheap (~$0.02/1M tokens), adequate for English legal text. Lock embedding model in `LegalCorpusVersion` to detect drift. |
| **Skill template engine** | Jinja2 | Standard. Already used by Django. |
| **CI lint runner** | `pytest` invocation of `manage.py verify_citations --strict` | Already how Django commands are tested. |
| **Concurrency primitive** | `pg_advisory_lock` | Already used by lease-AI (`manage.py reindex_lease_corpus`). |
| **Diff tool for lawyer review** | GitHub PRs (Klikk org) | Lawyer gets a read-only review-only collaborator seat. Comments inline. Approval = merge. |
| **Attestation storage** | YAML in `content/legal/attestations/` + signed-PDF in Vault33 (`apps.the_volt`) | Vault33 already has the FICA-grade document storage primitives. Reuse. SHA256 the PDF in the YAML for tamper-evidence. |
| **Webhook on corpus change** | Django `post_save` signal on `LegalCorpusVersion` → Plausible event + Slack notification | Lightweight. No external queue needed. |
| **MCP server (Phase B)** | `klikk-lease-law-rag` server (per lease-AI Phase 7); becomes `klikk-legal-rag` to scope-correctly | Reuses the existing planned MCP infra. Same FastAPI / `anthropic-mcp` stack. |
| **API for external consumers (if productised)** | DRF ViewSet on `/api/v1/legal-rag/` with throttle classes per tier | Already how Klikk exposes APIs. |

### File layout recap

```
content/legal/                       # canonical, source of truth
backend/apps/legal_rag/              # Django app — loader, queries, models, commands
backend/apps/legal_rag/skill_templates/   # Jinja templates for skill .md generation
.claude/skills/*/references/         # rendered output, checked in, lint-validated
docs/system/legal-rag-architecture.md  # the technical design doc (this plan, refactored)
content/cto/centralised-legal-rag-store-plan.md  # this plan (strategic)
content/cto/rha-citation-canonical-map.md  # seed reference, kept as historical artefact
```

---

## 12. Risks & open questions

### Risks I am pre-mitigating

**R1 — Lawyer is the bottleneck.** If the attorney is slow or unavailable, `mc_reviewed` facts cannot graduate to `lawyer_reviewed`. Mitigation: the system functions in `mc_reviewed` mode indefinitely — the lease AI Drafter can still use those facts, with the `legal_provisional` flag and disclaimers exposed to the user. External marketing claims and customer-facing audits gate on `lawyer_reviewed` only.

**R2 — YAML files in `content/legal/` are tempting to edit directly without going through the renderer.** Mitigation: `manage.py verify_citations --strict` blocks merge. Combined with the "edit YAML, not `.md`" convention in CONTRIBUTING.

**R3 — Embedding-model upgrade invalidates the entire ChromaDB index.** Mitigation: `LegalCorpusVersion` stores the embedding model name; upgrade is a full re-index + `corpus_version` bump, behind a deploy flag. Easier than dealing with drift.

**R4 — `content/legal/` grows large enough to bloat the git repo.** At ~50 statute facts + 50 case law + 50 pitfalls = 150 YAML files at ~500 bytes each = 75KB. Trivial. Even at 10x growth, still <1MB.

**R5 — Marketing copy depends on `mc_reviewed` facts before lawyer attests them.** Mitigation: Astro build fails if any rendered marketing copy depends on a fact with `verification_status != lawyer_reviewed`. Hard CI gate.

**R6 — Lease AI corpus migration breaks lease generation during cutover.** Mitigation: feature flag `features.use_centralised_legal_rag`. v1 reads from old `backend/apps/leases/lease_law_corpus/statutes/`; v2 reads from `apps.legal_rag`. 30-day overlap. Same pattern as lease-AI v1 → v2 cutover (decision 16 of lease-AI doc).

**R7 — A regulator asks for our legal-fact governance and we have only `mc_reviewed` facts attested.** Mitigation: the audit trail still defends "reasonable steps" — git history, MC review, CI lint, disclaimers rendered. Not bulletproof, but defensible. Move to first lawyer attestation before any externally-facing customer launch.

### Open questions for MC

1. **Lawyer retainer.** Are we engaging the FICA attorney for this or finding a separate rental-housing specialist? My recommendation: bundle with FICA attorney if they have rental practice; otherwise small Stellenbosch firm with rental-housing focus. Decision needed before Phase A week 2.
2. **Marketing copy gate.** Do we hard-block website builds on `lawyer_reviewed` only, or accept `mc_reviewed` facts on the pre-launch site? My recommendation: pre-launch, accept `mc_reviewed` with prominent disclaimer; post-launch (first paying customer), hard-block on `lawyer_reviewed`.
3. **Vault33 storage of opinion letters.** I'm assuming Vault33 (`apps.the_volt`) is the right home for the signed PDFs. Confirm? Or use plain S3 with KMS? Vault33 is more thematic; S3 is simpler.
4. **Skill regeneration cadence in CI.** Should `manage.py render_legal_skills` run on every PR (writing the `.md` back to the branch) or only on `main`? My recommendation: PR auto-renders; CI fails if branch is dirty after render. Same pattern as `pre-commit` for formatting.
5. **External API tier (productisation).** If we ever sell this — is the right buyer SA proptech competitors, SA conveyancers, or SA insurance? Out of scope for Phase A; relevant for Phase B+ pricing.
6. **The LOW-confidence sub-section rows (RHA s5(3)(f), s5(3)(h), s5(3)(m)).** Do we ship v1 lease AI with the `legal_provisional` flag visible, or hold v1 lease AI until lawyer arbitrates? My recommendation: ship with the flag visible — the lease AI is internal-only until the lawyer signs off the corpus anyway, per decision in lease-AI doc §3 "lawyer-blessed comes before external customer launch".

---

## 13. Phased delivery timeline

### Phase 0 — Decision lock (this document, half-day)

- CEO signs off the plan, picks decisions on the six open questions in §12.
- One-pager email to retained attorney describing scope of forthcoming quarterly review work.

### Phase A — Foundation (1-2 weeks)

| Day | Deliverable | Owner |
|---|---|---|
| 1 | `content/legal/` scaffolded with `_schema/`, `README.md`, `CHANGELOG.md`. Seed from canonical citation map → ~50 stub YAML files. | rentals-implementer |
| 1-2 | `backend/apps/legal_rag/` Django app scaffolded. `LegalFact`, `LegalFactVersion`, `LegalAttestation`, `LegalCorpusVersion` models + migration. | rentals-implementer |
| 2-3 | `manage.py sync_legal_facts` (YAML → Postgres, idempotent, advisory-locked). Unit tests. | rentals-implementer |
| 3-4 | `manage.py verify_citations --strict` (schema + cross-ref + lint). Hook into CI. | rentals-implementer |
| 4-5 | `manage.py render_legal_skills` (Jinja2 templates for the 11 POPIA-RHA references + 6 rental-master mixed references + `sa-rental-law.md`). | rentals-implementer + CTO |
| 5-7 | Migrate skill content into YAML. Re-render. CI green. | CTO + rentals-implementer |
| 7-9 | Subsume lease-AI statute corpus. Re-point Drafter/Reviewer queries. Lease-AI integration test green. | rentals-implementer + lease-AI team |
| 7-10 | Wire `query_*` Python API. ChromaDB indexer (`manage.py reindex_legal_corpus`). | rentals-implementer |
| 10-12 | First lawyer-attestation packet sent. Receive opinion letter. Write first attestation YAML. Flip statuses. | CTO + MC |
| 12-14 | Buffer + bug fixes + observability (Plausible event `legal_rag_query`, Sentry on `LegalFactNotFound`). | rentals-implementer |

**Phase A exit criteria:**

- All three skill `references/` directories regenerated and CI-validated.
- Lease AI runs end-to-end against `content/legal/` statute facts (clause library still owned by lease-AI corpus).
- One lawyer attestation YAML on disk, with at least 10 HIGH-confidence facts at `lawyer_reviewed`.
- CI lint blocks unknown statute citations across the repo.

### Phase B — Hardening + MCP carve-out (2-3 weeks; aligns with lease-AI Phase 7)

| Week | Deliverable |
|---|---|
| Week 4 | DRF `/api/v1/legal-rag/` read-only ViewSet for Astro website builds. Tier-scoped auth. |
| Week 4 | Marketing copy in `content/website/copy/` re-points to `legalRag.queryFact()` at build time. Hard-gate on `lawyer_reviewed`. |
| Week 5 | MCP server `klikk-legal-rag` (extracts from `apps.legal_rag`). Resources + Tools per §9. Internal Klikk consumer first; external auth deferred. |
| Week 5 | Lease-AI Drafter/Reviewer migrate from Python imports to MCP tool calls — proves the v2 transport. |
| Week 6 | Second quarterly attestation (more facts → `lawyer_reviewed`). Marketing pages unblocked. |
| Week 6 | Public-tier MCP authentication (if productisation gate passed). |

### Phase C — Productisation (deferred, when business case lands)

- External tier authentication + rate limits.
- Pricing tiers per §9.
- Documentation site for external developers.
- Vault33 integration as alternative backing store.

---

## Changelog

- 2026-05-12 — initial draft by CTO agent. Sources: `content/cto/rha-citation-canonical-map.md`, `docs/system/lease-ai-agent-architecture.md`, three skill `references/` directories (24 `.md` files surveyed), `content/README.md`, `CLAUDE.md`. All architectural decisions ranked; tech stack picks committed; phased timeline locked at 4-6 weeks for Phase A+B.
