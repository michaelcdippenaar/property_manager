# Owner Classification Summary

**Classified:** 2026-04-06
**Folder:** /tmp/za-doc-test/pty_ltd_complete/
**Files processed:** 8

---

## Entity

| Field | Value |
|---|---|
| Entity Name | Bergvliet Properties (Pty) Ltd |
| Entity Type | Company — Private (Pty) Ltd |
| Registration Number | 2019/087432/07 |
| Registration Date | 2019-05-14 |
| CIPC Status | Active |
| Registered Address | 34 Vineyard Close, Bergvliet, Cape Town, 7945 |
| Owned by Trust | No |

---

## FICA Status: COMPLETE (with advisory flags)

| Status | Document | File | Detail |
|---|---|---|---|
| FOUND | SA ID — Pieter Johannes Van der Berg | pieter_id.txt | ID 7503065023082 — certified 2026-01-15 |
| FOUND | SA ID — Annelie Van der Berg | annelie_id.txt | ID 7811190045087 — certified 2026-01-15 |
| FOUND | Bank Confirmation Letter | bank_confirmation.txt | Nedbank — Business Current Account ****3847 — dated 2026-03-10 |
| FOUND | Proof of Address | proof_of_address.txt | City of Cape Town Municipal Account — 2026-03-31 — VALID (6 days old) |
| FOUND | SARS Income Tax Registration | tax_certificate.txt | Tax number 9876543210 — registered 2019-07-01 |

**Missing:** None

**Advisory flags:**
- No VAT registration document found. Confirm whether Bergvliet Properties (Pty) Ltd is VAT registered. If yes, a VAT certificate is required for FICA completeness.
- No shareholder register (CoR14.1) or equivalent was found. FICA requires certified IDs for all persons holding 25% or more beneficial interest. The two directors have been identified and their IDs collected, but if any third-party shareholders hold 25%+ interest their IDs must also be obtained.

---

## CIPC Status: NEEDS REVIEW

| Status | Document | File | Detail |
|---|---|---|---|
| FOUND | CoR14.3 — Registration Certificate | registration_certificate.txt | Active — Reg. No. 2019/087432/07 — incorporated 2019-05-14 |
| FOUND | CoR39 — Notice of Directors | directors_notice.txt | 2 directors: Pieter Johannes Van der Berg, Annelie Van der Berg — filed 2019-05-14 |
| FOUND | CoR15.1A — Memorandum of Incorporation | moi.txt | Standard MOI adopted 2019-05-14 — 1,000 ordinary shares, no par value |
| MISSING | CoR123 — Annual Return | — | Company registered 2019; no annual return in the document set |

**Flags:**
- No CoR123 Annual Return found. Bergvliet Properties (Pty) Ltd was registered on 2019-05-14 — nearly 7 years ago. Annual returns must be filed each year with CIPC. Absence of this document in the folder does not necessarily mean returns were not filed, but the owner should be asked to supply the most recent CoR123 or confirm via CIPC's online portal that annual returns are up to date. Non-filing can result in deregistration.

---

## Director — ID Cross-Check

| Director (CoR39) | ID on CoR39 | ID Document Found | Match |
|---|---|---|---|
| Pieter Johannes Van der Berg | 7503065023082 | pieter_id.txt — 7503065023082 | YES |
| Annelie Van der Berg | 7811190045087 | annelie_id.txt — 7811190045087 | YES |

Both directors have corresponding certified ID copies. IDs match CoR39 exactly.

---

## Summary Verdict

All core FICA and CIPC documents are present and cross-referenced. The FICA file is considered **complete** for onboarding. The CIPC file is **needs_review** solely because no annual return (CoR123) was included in the document set — this should be requested or verified directly with CIPC before final onboarding approval.

**Recommended next steps:**
1. Ask the owner to supply or confirm the most recent CoR123 annual return (or provide CIPC confirmation number).
2. Confirm whether the company is VAT registered, and collect VAT certificate if applicable.
3. Confirm whether any shareholders (other than the two directors) hold 25%+ beneficial interest, and collect certified IDs if so.

`owner_classification.json` written to: `.claude/skills/za-company-doc-classifier-workspace/iteration-1/eval-pty-ltd-complete/with_skill/outputs/`
