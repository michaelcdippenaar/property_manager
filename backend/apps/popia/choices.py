"""
apps/popia/choices.py

POPIA-derived enum choices reused across business models. Imported as the
field choices on every PI-bearing model during the multi-tenant rollout
(see docs/compliance/popia-klikk-rentals-brief.md and
~/.claude/plans/fuzzy-giggling-squid.md).

Why a dedicated module
----------------------

Putting these here (rather than per-app or in a "shared utils") keeps the
POPIA vocabulary in one place — when the Information Regulator updates
the recognised lawful bases or retention guidance (see the 2025 Amendment
Regulations and the 3 Dec 2024 Direct Marketing Guidance Note), exactly
one file needs to change. Every model field is just a reference.

These are pure Python enums (Django `TextChoices`); no DB tables, no
migrations needed when added to a new model — only when the choices
themselves change.
"""

from __future__ import annotations

from django.db import models


class LawfulBasis(models.TextChoices):
    """
    POPIA s11(1) — the lawful processing bases.

    For a typical Klikk rental flow:
      - **CONTRACT** is the default basis for tenant + landlord PI captured
        during lease application and management — performance of a contract.
      - **LEGAL_OBLIGATION** applies to FICA / EAAB compliance documents
        the agency is required to retain by law.
      - **CONSENT** is required for direct marketing (s69 + 2024 DM
        Guidance Note) and for AI-assisted features that send PI
        cross-border to Anthropic (s72 read with s11(1)(a)).
      - **LEGITIMATE_INTEREST** is a residual basis — must pass the
        balancing test (subject's rights vs. processor's interest). Avoid
        unless explicitly justified.
      - **VITAL_INTEREST**, **PUBLIC_INTEREST** and **OPERATOR_INSTRUCTION**
        cover edge cases. ``OPERATOR_INSTRUCTION`` is the s21 basis under
        which Klikk-the-platform processes on behalf of an agency RP.
    """

    CONSENT = "consent", "Consent (s11(1)(a))"
    CONTRACT = "contract", "Performance of contract (s11(1)(b))"
    LEGAL_OBLIGATION = "legal_obligation", "Compliance with legal obligation (s11(1)(c))"
    VITAL_INTEREST = "vital_interest", "Protect vital interest (s11(1)(d))"
    PUBLIC_INTEREST = "public_interest", "Public interest / public function (s11(1)(e))"
    LEGITIMATE_INTEREST = "legitimate_interest", "Legitimate interest (s11(1)(f))"
    OPERATOR_INSTRUCTION = "operator_instruction", "Processing on operator instruction (s21)"


class RetentionPolicy(models.TextChoices):
    """
    POPIA s14 retention policies — informational at field level; consumed
    by the (later) retention/anonymisation cron job.

    Each choice maps to a concrete retention period:
      - **LEASE_LIFETIME** — keep until the lease has expired AND no
        outstanding obligations remain (most rental records).
      - **FICA_5YR** — Financial Intelligence Centre Act s42 / s43:
        5 years from end of business relationship.
      - **FICA_7YR** — older audit-history obligations under JSE / SARS
        guidance for trust-account-bearing records.
      - **RHA_3YR** — Rental Housing Act dispute records: 3 years.
      - **AUDIT_PERMANENT** — append-only audit trail; never delete,
        anonymise subject references after the parent's retention window.
      - **AI_CHAT_90D** — AI guide / assistant interactions: 90 days
        unless explicitly retained by the user; cross-border-transfer
        liability minimisation.
      - **MARKETING_CONSENT_LIFETIME** — direct marketing consent /
        opt-out records, retained for the duration of the relationship
        + 5 years (Information Regulator 2024 DM Guidance).
      - **NONE** — no automated retention; manual or external policy
        applies. Use sparingly; review at audit time.
    """

    LEASE_LIFETIME = "lease_lifetime", "Lease lifetime + obligations cleared"
    FICA_5YR = "fica_5yr", "FICA — 5 years from end of relationship"
    FICA_7YR = "fica_7yr", "FICA / SARS — 7 years"
    RHA_3YR = "rha_3yr", "RHA dispute records — 3 years"
    AUDIT_PERMANENT = "audit_permanent", "Audit trail — permanent (anonymise references)"
    AI_CHAT_90D = "ai_chat_90d", "AI chat / assistant — 90 days"
    MARKETING_CONSENT_LIFETIME = "marketing_consent_lifetime", "Marketing consent record"
    NONE = "none", "No automated retention"


class AnonymisationReason(models.TextChoices):
    """
    Why a record was anonymised. Set on the model row at anonymisation
    time alongside ``anonymised_at`` so a future audit / DSAR response can
    explain *why* the PI was scrubbed, not just *that* it was scrubbed.

    POPIA s23 (access) and s24 (correction / erasure) require that the
    responsible party be able to demonstrate the lawful basis for any
    anonymisation event.
    """

    DSAR_DELETION = "dsar_deletion", "Subject requested deletion (s24)"
    RETENTION_EXPIRED = "retention_expired", "Retention window expired (s14)"
    AGENCY_OFFBOARDING = "agency_offboarding", "Agency closed account / cancelled subscription"
    DATA_QUALITY = "data_quality", "Record corrected — superseded data anonymised"
    OPERATOR_DECISION = "operator_decision", "Klikk operator decision (rare)"
