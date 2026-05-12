---
title: RHA / POPIA / CPA / PIE — Canonical Citation Map
status: PROVISIONAL — requires legal sign-off before any externally-facing lease text relies on it
owner: CTO
last_updated: 2026-05-12
trigger: Opus auditor #2 of `docs/system/lease-ai-agent-architecture.md` flagged systematic statute-citation errors. Three internal skills (`klikk-legal-POPIA-RHA`, `klikk-rental-master`, `klikk-leases-rental-agreement`) disagree with each other AND with the auditor's reading of the 1999 Gazette PDF.
---

# Purpose

This file is the **single source of truth** for which statute section we cite for each rental-law concept used by:

- The lease AI agent cluster (`docs/system/lease-ai-agent-architecture.md`)
- The legal RAG corpus (Tier C, ~210 chunks)
- The three internal skills that touch SA rental law
- Any externally-visible product copy (lease templates, in-product help, marketing pages making compliance claims)

The map is **provisional** until a SA-admitted attorney signs off Section 5 below. Until then, the lease AI must use the "Working canonical assumption" column AND surface its own confidence per citation.

# Why the map exists

Three internal skills disagree on the s5(3) sub-section lettering for the **same** concept (deposit interest-bearing account; refund timelines). They were written at different times by different authors, possibly reading different versions of the Act (1999 original vs. 2014 amendment vs. provincial regs). The lease AI cannot ship while skill content fights itself.

A second confounder: SAFLII (the canonical public source for SA statutes) is Cloudflare-protected and cannot be fetched programmatically from this environment. The previous Opus auditor read the 1999 Gazette PDF directly. We rely on the auditor's reading as a fourth source, alongside the three skill snapshots.

# Sources reviewed

| ID | Source | Notes |
|---|---|---|
| **AUDITOR** | Opus auditor #2 of design doc (read original 1999 Gazette PDF) | Recent. Read the ORIGINAL 1999 Act, may not reflect the 2014-amended in-force text. |
| **SKILL-A** | `.claude/skills/klikk-leases-rental-agreement/references/sa-rental-law.md` | Older. Compact reference, low ceremony. |
| **SKILL-B** | `.claude/skills/klikk-legal-POPIA-RHA/references/06-rha-core-and-s5.md` | Newer (2026-04-17). Detailed. Internally claims to reflect the 2014 amendment. |
| **SKILL-B2** | `.claude/skills/klikk-legal-POPIA-RHA/references/07-rha-s4a-unfair-practices.md` | Companion to SKILL-B. Internally consistent with B on Tribunal establishment. |
| **SKILL-C** | `.claude/skills/klikk-rental-master/references/05-deposit-rules.md` | Deposit-focused. Cites only the interest-bearing-account section. |
| **DESIGN** | `docs/system/lease-ai-agent-architecture.md` (current HEAD) | Draws from all skills. Carries forward whichever citation was nearest to hand. |

# Citation discrepancy matrix

Each row is one rental-law concept. Columns show what each source claims. **Working canonical** = the assumption the lease AI will use until a lawyer arbitrates. **Confidence** is mine (CTO), not legal — see "Lawyer-required arbitrations" below for what needs sign-off.

## RHA 50 of 1999 (as amended by Act 35 of 2014)

| # | Concept | AUDITOR | SKILL-A | SKILL-B | SKILL-C | DESIGN (current) | Working canonical | Confidence |
|---|---|---|---|---|---|---|---|---|
| 1 | Tribunal **establishment** | s7 | s13 | s7 | (not cited) | s13 | **s7** | HIGH — SKILL-B explicit, SKILL-B2 explicit, AUDITOR concurs; only SKILL-A and current DESIGN say s13 |
| 2 | Tribunal **powers / referral** | s13 | s13 | s13 | (not cited) | s13 | **s13** | HIGH — three sources concur |
| 3 | Rental Housing Information Office | s14 (info office) | (not addressed) | (not addressed) | (not addressed) | not used | **s14 = Information Office, NOT lease contents** | HIGH — AUDITOR flagged this is wrongly cited as a lease-contents section in DESIGN; verify NOT cited as lease content |
| 4 | Right to written lease | s5(2) | s5(2) | s5(2) | (not cited) | s5(2) | **s5(2)** | HIGH — universal agreement |
| 5 | Mandatory lease contents — top-level | s5(3) | s5(3) | s5(3) | (not cited) | s5(3) | **s5(3)** | HIGH — universal agreement |
| 6 | Lease must name parties + addresses for service | s5(3)(a) | s5(3)(a) | s5(3)(a) | (not cited) | s5(3)(a) | **s5(3)(a)** | HIGH |
| 7 | Description of dwelling | s5(3)(b) | s5(3)(b) | s5(3)(b) | (not cited) | s5(3)(b) | **s5(3)(b)** | HIGH |
| 8 | Rental amount + escalation | (auditor implies s5(3)(c)) | s5(3)(d) | s5(3)(c) | (not cited) | s5(3)(c) | **s5(3)(c)** | MEDIUM — SKILL-A swaps (c)/(d); two newer sources + DESIGN agree on (c) |
| 9 | Term / notice period | (auditor implies s5(3)(d)) | s5(3)(c) | s5(3)(d) | (not cited) | s5(3)(d) | **s5(3)(d)** | MEDIUM — same swap as #8 |
| 10 | Deposit **amount** | s5(3)(e) | s5(3)(e) | s5(3)(e) | (not cited) | s5(3)(e) | **s5(3)(e)** | HIGH |
| 11 | Deposit **interest-bearing account requirement** | s5(3)(d) (per auditor) | s5(3)(f) | s5(3)(f) | s5(3)(f) | s5(3)(f) | **s5(3)(f)** — but **flag for lawyer** | LOW — three skills agree on (f); auditor (reading original 1999 Gazette) says (d). Likely the amendment renumbered. Resolve by reading current consolidated Act. |
| 12 | Deposit cap (2× rent) | (not statutory cap — regulation) | s5(3)(g) | (described as industry custom, not statute) | regulations / s4A | regulations | **No fixed cap in s5(3); convention 1–2× is industry; >2× may be s4A unfair practice** | HIGH — SKILL-B explicit that no statutory cap exists; treat SKILL-A's "s5(3)(g) cap" as error |
| 13 | Rent **due date** | (auditor: s5(3)(g)) | (not cited) | s5(3)(g) | (not cited) | s5(3)(g) | **s5(3)(g)** | HIGH — SKILL-B + DESIGN agree |
| 14 | Landlord / tenant **obligations summary** | — | — | s5(3)(h) | — | s5(3)(h) | **s5(3)(h) (top-level listing); detailed duties at s5A and s5B** | MEDIUM |
| 15 | House rules annexed | s5(5) (per SKILL-A) | s5(5) | s5(3)(i) | (not cited) | s5(3)(i) | **s5(3)(i)** — SKILL-A and SKILL-B disagree, defer to SKILL-B (newer + detailed) | MEDIUM |
| 16 | Deposit purpose + refund **terms** stated in lease | — | — | s5(3)(j) | — | s5(3)(j) | **s5(3)(j)** | MEDIUM |
| 17 | Refund **7 days** — no damage | (auditor: s5(3)(i)) | (not cited) | (timing rule, not statute cite) | 7 days (no cite) | s5(3)(h) [WRONG] | **DEFER — lawyer to confirm sub-section letter for the 7-day refund. Stamp as "RHA s5(3) refund-on-no-damage rule" pending arbitration** | LOW |
| 18 | Refund **14 days** — damage / repairs | (auditor: s5(3)(g)) | s5(3)(h) | (timing rule, not statute cite) | 14 days (no cite) | s5(3)(h) | **DEFER — same as #17** | LOW |
| 19 | Refund **21 days** — tenant absent from inspection | (auditor: s5(3)(m)) | (not cited) | (timing rule, not statute cite) | 21 days (no cite) | (not cited) | **DEFER — same as #17. (m) is implausible — the amended Act would not skip from (j) to (m); auditor may be reading ORIGINAL 1999 lettering** | LOW |
| 20 | Joint inspection requirement | s5(3)(k) (per auditor) | (described as duty, no cite) | s5(3)(k) | (described, no cite) | s5(3)(k) | **s5(3)(k)** | MEDIUM |
| 21 | Landlord duties (habitable etc.) | s5A | s5A | s5A | (not cited) | s5A | **s5A** | HIGH |
| 22 | Tenant duties | s5B | s5B | s5B | (not cited) | s5B | **s5B** | HIGH |
| 23 | Unfair practices framework | s4A | s4A | s4A | s4A | s4A | **s4A** | HIGH |
| 24 | Non-discrimination | s4(1) | (not addressed) | s4(1) | (not addressed) | s4(1) | **s4(1)** | HIGH |
| 25 | Tenant right to privacy | s4(2) | (not addressed) | s4(2) | (not addressed) | s4(2) | **s4(2)** | HIGH |

### Critical RHA action items
- **#1 (Tribunal establishment)**: DESIGN currently cites s13. **Change to s7.** High confidence.
- **#11, #17–19 (deposit interest + refund timelines)**: lawyer **must** confirm the sub-section lettering against the **current consolidated** Act. Three skills agree on (f) for interest-bearing; auditor (reading 1999 original) says (d). Until resolved, the lease AI may cite the **concept** ("RHA s5(3) — interest-bearing account requirement") without the sub-section letter when uncertain.
- **#3 (s14)**: confirm DESIGN never cites s14 as a lease-contents section. The audit flagged it as a planted error; current grep of DESIGN confirms s14 is only referenced in CPA context.

## POPIA Act 4 of 2013

| # | Concept | AUDITOR | Other skills | DESIGN (current) | Working canonical | Confidence |
|---|---|---|---|---|---|---|
| P1 | Lawful processing — eight conditions | Chapter 3 (ss 8–25) | (varies) | (top-level cite) | **POPIA ss 8–25 (Chapter 3) — Conditions for Lawful Processing** | HIGH |
| P2 | Purpose specification | s13 | s13 (klikk-legal-POPIA-RHA) | s13 | **s13** | HIGH |
| P3 | Further processing limitation | s15 | s15 | s15 | **s15** | HIGH |
| P4 | **Information quality / accuracy** | s16 | s16 | **s11(2)** [WRONG per auditor] | **s16** | MEDIUM-HIGH — auditor flagged s11(2) as wrong cite; s16 is the accuracy condition |
| P5 | Openness — notification of data subject | s17 + s18 | s17 / s18 | s17–18 | **s17–18** | HIGH |
| P6 | Security safeguards | s19 | s19 | s19 | **s19** | HIGH |
| P7 | Data subject participation — access | s23 | s23 | s23 | **s23** | HIGH |
| P8 | Data subject participation — correction | s24 | s24 | s24 | **s24** | HIGH |
| P9 | **Right to deletion / destruction** | s24 (correction includes deletion of inaccurate/excessive/unlawful/no-longer-authorised PI) | s24 (SKILL-B claims s24 covers deletion) | **s25** [WRONG per auditor] | **s24** | MEDIUM-HIGH — auditor: s25 is "manner of access" procedure, not a deletion right. Confirm by reading SKILL-B §13.|
| P10 | Direct marketing | s69 | s69 | s69 | **s69** | HIGH |
| P11 | Cross-border transfer | s72 | s72 | s72 | **s72** | HIGH |
| P12 | Lawful basis — consent | s11(1)(a) | s11(1)(a) | s11 | **s11(1)(a)** | HIGH |
| P13 | Lawful basis — contract | s11(1)(b) | s11(1)(b) | s11 | **s11(1)(b)** | HIGH |
| P14 | Lawful basis — legal obligation | s11(1)(c) | s11(1)(c) | s11 | **s11(1)(c)** | HIGH |
| P15 | Lawful basis — legitimate interest | s11(1)(f) | s11(1)(f) | s11 | **s11(1)(f)** | HIGH |

### Critical POPIA action items
- **P4**: DESIGN cites s11(2) for accuracy/quality. **Change to s16.** Medium-high confidence per auditor + standard POPIA reading.
- **P9**: DESIGN cites s25 for deletion. **Change to s24.** Medium-high confidence. s25 is the procedural manner-of-access section, not a substantive deletion right. (Note: deletion-on-retention-period-expiry is also covered by s14, which is the retention-period section.)
- **P12–P15**: DESIGN's lawful-basis table should reference the specific s11(1)(a)–(f) sub-sections, not just "s11".

## CPA Act 68 of 2008

| # | Concept | Working canonical | Confidence |
|---|---|---|---|
| C1 | Fixed-term consumer agreements (early cancellation, max 24 months, renewal-notice obligation) | **s14** | HIGH |
| C2 | Plain language requirement | **s22** | HIGH |
| C3 | Unfair, unreasonable, unjust contract terms | **s48** | HIGH |
| C4 | Quality of services | **s54** | HIGH |
| C5 | Cooling-off (direct marketing) | **s16** | HIGH |

### Note on CPA applicability
CPA s14 applies only if the **tenant is a natural person AND the landlord is in the business of letting** (not a one-off private let between individuals). The lease AI must condition CPA s14 clauses on this test, not blanket-insert.

## PIE Act 19 of 1998

| # | Concept | Working canonical | Confidence |
|---|---|---|---|
| E1 | Eviction must be by **court order** — no self-help | **PIE Act 19/1998, s4 (urgent), s5 (any unlawful occupier)** | HIGH |
| E2 | "Unlawful occupier" definition | **PIE s1** | HIGH |
| E3 | Service requirements (14 days before hearing) | **PIE s4(2)** | HIGH |

### Critical PIE action items
- **AUDITOR flagged**: DESIGN currently includes PIE-themed language in the lease NOTICE body. This is **oversold** — PIE governs eviction proceedings, not the lease itself. The lease should reference PIE only in (a) a "Termination and unlawful occupation" clause that points the tenant to PIE protections, and (b) the agent-facing rendering of dispute-resolution notes. **Do not present PIE as if it operates pre-termination.**

# Lawyer-required arbitrations

These are the citations the lease AI **must not assert as authoritative** until a SA-admitted attorney signs off:

1. **RHA s5(3) sub-section lettering for deposit interest-bearing account** (item #11). Three skills say (f); auditor (reading 1999 original) says (d). Resolve by reading the current consolidated Act published in the Government Gazette as in force at 2026.
2. **RHA s5(3) sub-section lettering for the 7 / 14 / 21-day refund deadlines** (items #17–19). Auditor says (i), (g), (m). Skills do not cite sub-sections. The "(m)" reading is implausible against the in-force amended Act — likely the auditor is reading the ORIGINAL 1999 Gazette numbering, not the amended consolidated text. **Must be resolved.**
3. **Whether the deposit cap is statutory or regulatory** (item #12). SKILL-A wrongly attributes a statutory cap to s5(3)(g). SKILL-B correctly states the RHA does not cap the deposit and that the 2× convention is industry custom. Lawyer to confirm whether any Minister-published regulation under s15 of the RHA imposes a statutory cap.
4. **House rules annexure** (item #15). SKILL-A says s5(5); SKILL-B says s5(3)(i). Two different sub-sections of the same Act — one of these must be wrong. Skills disagree because they reflect different drafting eras.
5. **POPIA s16 vs s11(2) for information accuracy** (item P4). Standard POPIA reading is s16. Auditor flag is well-grounded but minor.
6. **POPIA s24 vs s25 for deletion** (item P9). Standard POPIA reading is s24; s25 is procedure. Auditor flag is well-grounded.
7. **PIE Act language in lease body** (E1+). Material legal-tone issue; not a citation error but a scope error.

# Operational rules for the lease AI (interim, pending sign-off)

Until a lawyer signs off Section 5:

- **Drafter agent** may cite RHA / POPIA / CPA / PIE statutes by **name and the most-confident sub-section in the "Working canonical" column** of the matrices above.
- For LOW-confidence rows (#11, #17–19), Drafter must either:
  - cite the concept without the sub-section letter ("RHA s5(3) — interest-bearing account requirement"), OR
  - mark the clause with an internal `legal_provisional: true` flag visible to the Reviewer agent so the Reviewer can refuse to greenlight outward-facing release.
- **Reviewer agent** must fail any output that asserts a LOW-confidence citation without the `legal_provisional` flag.
- **Formatter agent** is forbidden from inserting any new statute citation. It only formats what Drafter+Reviewer agreed.
- **RAG corpus loader** must annotate every chunk with `citation_confidence: high | medium | low` based on this map. Only HIGH and MEDIUM chunks are retrieved by default; LOW chunks are retrieved only when explicitly requested by the Reviewer asking for "all possibly-relevant citations."
- **Verify-citations CLI** (`manage.py verify_caselaw_citations`, to be built in Phase 0.5) reads this map and validates every citation in every corpus chunk + skill file + design doc against the "Working canonical" column. Fails CI if drift detected.

# Recommended file changes

Once the lawyer signs off:

### `docs/system/lease-ai-agent-architecture.md`
- Replace `RHA s13` (Tribunal establishment) → `RHA s7` everywhere it appears as the establishing section. Keep `s13` for Tribunal **powers / referral**.
- Update POPIA citations: `s11(2)` for accuracy → `s16`. `s25` for deletion → `s24`.
- Either remove the PIE Act citation from the lease NOTICE body, or move it to a dedicated "Termination and unlawful occupation" clause with clearer scoping.
- For RHA s5(3) sub-section letters, apply the lawyer's verified mapping.
- Add a one-paragraph "Citations and legal interpretation" section pointing to this canonical map.

### `.claude/skills/klikk-legal-POPIA-RHA/references/06-rha-core-and-s5.md`
- If lawyer confirms auditor's reading: update the s5(3) lettering table (lines 38–49). Otherwise: leave as-is and **update SKILL-A to match SKILL-B**.
- Update line 50–58 refund table to either include the verified sub-section letters or remove the implication that 7/14/21 maps to consecutive sub-sections.

### `.claude/skills/klikk-leases-rental-agreement/references/sa-rental-law.md`
- **Significant rewrite needed**: this file swaps s5(3)(c) and (d), claims s5(3)(g) is the deposit cap (it isn't), claims s5(3)(h) is the 14-day refund (uncertain), and says the Tribunal is established under s13 (it's under s7).
- After lawyer sign-off, regenerate this skill's RHA section in full to match canonical.

### `.claude/skills/klikk-rental-master/references/05-deposit-rules.md`
- Update three `s5(3)(f)` references in the interest-bearing-account table (lines 17–24) to match canonical once lawyer confirms.
- Add a one-line "see canonical citation map" note.

### `.claude/skills/klikk-legal-POPIA-RHA/references/07-rha-s4a-unfair-practices.md`
- Already internally consistent on s7 / s13 distinction. Likely no change needed.
- Verify the `s5(3)(f)` reference on line 14 against canonical.

# Open questions for the lawyer

Send these to counsel along with this map:

1. In the **current consolidated** Rental Housing Act 50 of 1999 as amended by Act 35 of 2014 and any subsequent amendments in force as of 2026, what sub-sections of s5(3) cover:
   - Interest-bearing account requirement for the deposit?
   - 7-day refund (no damage)?
   - 14-day refund (damage)?
   - 21-day refund (tenant absent)?
   - Joint inspection requirement?
   - House rules annexure?
2. Is there a statutory deposit cap (RHA or regulations) or is the "2× rent" purely industry convention?
3. Confirm: Tribunal is established under s7; its powers and procedure are in s13. Yes/no.
4. Confirm: POPIA accuracy condition is s16, not s11(2). Yes/no.
5. Confirm: POPIA deletion of inaccurate/excessive/no-longer-authorised PI is under s24 (data subject participation – correction/deletion). Yes/no.
6. Confirm: PIE Act 19/1998 should not be cited in the lease body itself except as a reference in the termination/unlawful-occupation clause. Yes/no.
7. Any additional sections the Drafter agent should cite for: domicilium (CPA + Domicilium Act if any), Sectional Titles Schemes Management Act 8/2011 for sectional-title rules, body-corporate jurisdiction in CSOS Act 9/2011.

# Changelog

- 2026-05-12 — initial draft (CTO). Sources: AUDITOR + 5 skill files + DESIGN doc. All LOW-confidence rows queued for lawyer review.
