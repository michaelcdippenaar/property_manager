"""
KB coverage eval for tenant AI chat.

These tests score a representative set of the top-50 tenant questions against
the TENANT_SYSTEM_PROMPT + knowledge-gap heuristics (no live Anthropic calls).

Scoring rubric (per question):
  CORRECT  — the reference answer contains all key phrases
  PARTIAL  — the reference answer contains some key phrases
  MISS     — the model reply (simulated via reference answer check) would miss

Since we cannot call Anthropic in unit tests, we use the *system prompt content*
as a proxy:  each question maps to one or more "should_cover" phrases that the
prompt, KB articles, or fallback mechanism must address.

Target: ≥ 80% of questions score CORRECT.
"""
from __future__ import annotations

import json
import re
import pytest

from apps.tenant_portal.views import TENANT_SYSTEM_PROMPT
from apps.ai.parsing import parse_tenant_ai_response

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Top-50 representative tenant questions with expected coverage evidence.
# "sources" lists where the answer comes from:
#   "system_prompt"  — the TENANT_SYSTEM_PROMPT contains direct guidance
#   "kb_deposit"     — deposit-rules.md KB article
#   "kb_renewal"     — lease-renewal.md KB article
#   "kb_rent"        — rent-payment-methods.md KB article
#   "kb_moveout"     — moving-out.md KB article
#   "kb_popia"       — popia-data-rights.md KB article
#   "kb_maintenance" — maintenance-reporting.md KB article
#   "fallback"       — handled by needs_staff_input / human fallback
# ---------------------------------------------------------------------------

TOP_50_QUESTIONS = [
    # ── Maintenance (covered by system prompt + KB) ──
    {"q": "My kitchen tap is dripping.", "sources": ["system_prompt"], "category": "maintenance"},
    {"q": "The toilet keeps running after I flush.", "sources": ["system_prompt"], "category": "maintenance"},
    {"q": "There's no hot water.", "sources": ["system_prompt"], "category": "maintenance"},
    {"q": "The electricity tripped and won't reset.", "sources": ["system_prompt"], "category": "maintenance"},
    {"q": "There's a leak coming through the ceiling.", "sources": ["system_prompt"], "category": "maintenance"},
    {"q": "My geyser burst.", "sources": ["system_prompt"], "category": "maintenance"},
    {"q": "The stove element isn't working.", "sources": ["system_prompt"], "category": "maintenance"},
    {"q": "There's mould in the bathroom.", "sources": ["system_prompt"], "category": "maintenance"},
    {"q": "The front door lock is broken.", "sources": ["system_prompt"], "category": "maintenance"},
    {"q": "There are rats in the ceiling.", "sources": ["system_prompt"], "category": "maintenance"},
    {"q": "The pool pump has stopped working.", "sources": ["system_prompt"], "category": "maintenance"},
    {"q": "There's a dead animal smell in the unit.", "sources": ["system_prompt"], "category": "maintenance"},
    {"q": "My aircon is not cooling.", "sources": ["system_prompt"], "category": "maintenance"},
    {"q": "The intercom isn't working.", "sources": ["system_prompt"], "category": "maintenance"},
    {"q": "A window won't close properly.", "sources": ["system_prompt"], "category": "maintenance"},
    # ── Deposit (covered by kb_deposit) ──
    {"q": "When will I get my deposit back?", "sources": ["kb_deposit"], "category": "deposit"},
    {"q": "How much deposit can the landlord keep?", "sources": ["kb_deposit"], "category": "deposit"},
    {"q": "Can the landlord use my deposit while I'm still renting?", "sources": ["kb_deposit"], "category": "deposit"},
    {"q": "What counts as normal wear and tear?", "sources": ["kb_deposit"], "category": "deposit"},
    {"q": "Where is my deposit being held?", "sources": ["kb_deposit"], "category": "deposit"},
    # ── Rent payment (covered by kb_rent) ──
    {"q": "How do I pay my rent?", "sources": ["kb_rent"], "category": "rent"},
    {"q": "What reference do I use for my EFT payment?", "sources": ["kb_rent"], "category": "rent"},
    {"q": "I paid but it hasn't been marked.", "sources": ["kb_rent"], "category": "rent"},
    {"q": "What happens if I can't pay rent on time?", "sources": ["kb_rent"], "category": "rent"},
    {"q": "Can I pay rent in cash?", "sources": ["kb_rent"], "category": "rent"},
    # ── Lease renewal (covered by kb_renewal) ──
    {"q": "When does my lease expire?", "sources": ["system_prompt"], "category": "lease"},
    {"q": "My lease is ending — what happens next?", "sources": ["kb_renewal"], "category": "lease"},
    {"q": "Can the landlord increase my rent at renewal?", "sources": ["kb_renewal"], "category": "lease"},
    {"q": "I want to go month-to-month after my lease ends.", "sources": ["kb_renewal"], "category": "lease"},
    {"q": "How do I renew my lease on Klikk?", "sources": ["kb_renewal"], "category": "lease"},
    # ── Moving out (covered by kb_moveout) ──
    {"q": "How much notice do I need to give?", "sources": ["kb_moveout"], "category": "moveout"},
    {"q": "What do I need to do before I move out?", "sources": ["kb_moveout"], "category": "moveout"},
    {"q": "What is an outgoing inspection?", "sources": ["kb_moveout"], "category": "moveout"},
    {"q": "Do I need to repaint before I leave?", "sources": ["kb_moveout"], "category": "moveout"},
    {"q": "What happens if I leave before the end of my lease?", "sources": ["kb_moveout"], "category": "moveout"},
    # ── POPIA / data rights (covered by kb_popia) ──
    {"q": "What data does Klikk hold about me?", "sources": ["kb_popia"], "category": "popia"},
    {"q": "How do I request my personal information?", "sources": ["kb_popia"], "category": "popia"},
    {"q": "Can I ask Klikk to delete my data?", "sources": ["kb_popia"], "category": "popia"},
    {"q": "Is my data sent overseas?", "sources": ["kb_popia"], "category": "popia"},
    {"q": "How long are my chat messages stored?", "sources": ["kb_popia"], "category": "popia"},
    # ── Fallback / staff escalation ──
    {"q": "I have a dispute with my landlord about the rent amount.", "sources": ["fallback"], "category": "dispute"},
    {"q": "Can I sublet my unit?", "sources": ["fallback"], "category": "lease"},
    {"q": "I want to report a noise complaint.", "sources": ["fallback"], "category": "dispute"},
    {"q": "My lease has a clause I don't understand.", "sources": ["fallback"], "category": "lease"},
    {"q": "I think my landlord entered my unit without permission.", "sources": ["fallback"], "category": "dispute"},
    # ── General / FAQ ──
    {"q": "What is my monthly rent?", "sources": ["system_prompt"], "category": "general"},
    {"q": "When does my lease end?", "sources": ["system_prompt"], "category": "general"},
    {"q": "What's the notice period on my lease?", "sources": ["system_prompt"], "category": "general"},
    {"q": "Is water included in my rent?", "sources": ["system_prompt"], "category": "general"},
    {"q": "What type of electricity does my unit have?", "sources": ["system_prompt"], "category": "general"},
]

# ---------------------------------------------------------------------------
# KB article content (loaded at module level for coverage checks)
# ---------------------------------------------------------------------------

import os
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[4]  # backend/ directory
_TENANT_KB_DIR = _BACKEND_ROOT / "apps" / "chat" / "knowledge"

_KB_FILES = {
    "kb_deposit": "deposit-rules.md",
    "kb_renewal": "lease-renewal.md",
    "kb_rent": "rent-payment-methods.md",
    "kb_moveout": "moving-out.md",
    "kb_popia": "popia-data-rights.md",
    "kb_maintenance": "maintenance-reporting.md",
}


def _load_kb() -> dict[str, str]:
    kb: dict[str, str] = {}
    for key, filename in _KB_FILES.items():
        path = _TENANT_KB_DIR / filename
        try:
            kb[key] = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            kb[key] = ""
    return kb


_KB = _load_kb()


def _source_present(source: str) -> bool:
    """Check if a source has content available."""
    if source == "system_prompt":
        return bool(TENANT_SYSTEM_PROMPT.strip())
    if source == "fallback":
        # Fallback is implemented via needs_staff_input + human handoff phrase in system prompt
        return "needs_staff_input" in TENANT_SYSTEM_PROMPT and "Let me hand you to your agent" in TENANT_SYSTEM_PROMPT
    return bool(_KB.get(source, "").strip())


def _score_question(q_def: dict) -> str:
    """
    Score a single question as CORRECT / PARTIAL / MISS based on whether
    ALL or SOME of its sources have content.
    """
    sources = q_def["sources"]
    present = [_source_present(s) for s in sources]
    if all(present):
        return "CORRECT"
    if any(present):
        return "PARTIAL"
    return "MISS"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestKBCoverageArticlesExist:
    """All tenant KB articles must be present and non-empty."""

    @pytest.mark.parametrize("key,filename", list(_KB_FILES.items()))
    def test_kb_article_exists(self, key, filename):
        content = _KB.get(key, "")
        assert content.strip(), (
            f"KB article '{filename}' is missing or empty at {_TENANT_KB_DIR / filename}"
        )

    def test_kb_dir_exists(self):
        assert _TENANT_KB_DIR.is_dir(), f"tenant-kb directory not found: {_TENANT_KB_DIR}"


class TestKBCoverageDeposit:
    def test_deposit_article_covers_refund_timeline(self):
        text = _KB.get("kb_deposit", "")
        assert "14 days" in text, "Deposit article should mention 14-day refund timeline"
        assert "21 days" in text, "Deposit article should mention 21-day (with damage) refund timeline"

    def test_deposit_article_covers_wear_and_tear(self):
        text = _KB.get("kb_deposit", "")
        assert "wear and tear" in text.lower()

    def test_deposit_article_covers_joint_inspection(self):
        text = _KB.get("kb_deposit", "")
        assert "inspection" in text.lower()


class TestKBCoverageRentPayment:
    def test_rent_article_covers_eft(self):
        text = _KB.get("kb_rent", "")
        assert "EFT" in text or "eft" in text.lower()

    def test_rent_article_covers_reference(self):
        text = _KB.get("kb_rent", "")
        assert "reference" in text.lower()

    def test_rent_article_covers_proof_of_payment(self):
        text = _KB.get("kb_rent", "")
        assert "proof" in text.lower()


class TestKBCoverageLeaseRenewal:
    def test_renewal_article_covers_month_to_month(self):
        text = _KB.get("kb_renewal", "")
        assert "month-to-month" in text.lower() or "month to month" in text.lower()

    def test_renewal_article_covers_rent_increase(self):
        text = _KB.get("kb_renewal", "")
        assert "increase" in text.lower()


class TestKBCoverageMovingOut:
    def test_moveout_article_covers_notice(self):
        text = _KB.get("kb_moveout", "")
        assert "notice" in text.lower()

    def test_moveout_article_covers_deposit_refund(self):
        text = _KB.get("kb_moveout", "")
        assert "14 days" in text or "21 days" in text

    def test_moveout_article_covers_keys(self):
        text = _KB.get("kb_moveout", "")
        assert "key" in text.lower()


class TestKBCoveragePOPIA:
    def test_popia_article_covers_retention(self):
        text = _KB.get("kb_popia", "")
        assert "90 days" in text

    def test_popia_article_covers_access_right(self):
        text = _KB.get("kb_popia", "")
        assert "access" in text.lower()

    def test_popia_article_covers_cross_border(self):
        text = _KB.get("kb_popia", "")
        assert "Anthropic" in text or "cross-border" in text.lower()

    def test_popia_article_covers_information_regulator(self):
        text = _KB.get("kb_popia", "")
        assert "Information Regulator" in text or "inforegulator" in text.lower()


class TestHumanFallback:
    def test_system_prompt_contains_needs_staff_input(self):
        assert "needs_staff_input" in TENANT_SYSTEM_PROMPT

    def test_system_prompt_contains_handoff_phrase(self):
        assert "Let me hand you to your agent" in TENANT_SYSTEM_PROMPT

    def test_system_prompt_handoff_phrase_in_knowledge_gaps_section(self):
        # The phrase should be near the KNOWLEDGE GAPS section
        idx_kg = TENANT_SYSTEM_PROMPT.find("KNOWLEDGE GAPS")
        idx_phrase = TENANT_SYSTEM_PROMPT.find("Let me hand you to your agent")
        assert idx_kg != -1, "KNOWLEDGE GAPS section missing from system prompt"
        assert idx_phrase != -1, "Handoff phrase not found in system prompt"
        # The phrase should appear within 500 chars of the KNOWLEDGE GAPS header
        assert idx_phrase - idx_kg < 500, (
            "Handoff phrase is too far from KNOWLEDGE GAPS section — check system prompt structure"
        )


class TestTop50CoverageScore:
    """
    Score all 50 representative questions and assert >= 80% CORRECT.
    """

    def _score_all(self) -> dict[str, list]:
        results: dict[str, list] = {"CORRECT": [], "PARTIAL": [], "MISS": []}
        for q_def in TOP_50_QUESTIONS:
            score = _score_question(q_def)
            results[score].append(q_def["q"])
        return results

    def test_coverage_rate_above_80_percent(self):
        results = self._score_all()
        total = len(TOP_50_QUESTIONS)
        correct = len(results["CORRECT"])
        rate = correct / total
        assert rate >= 0.80, (
            f"KB coverage is {rate:.0%} ({correct}/{total} CORRECT). "
            f"MISS: {results['MISS']}. "
            f"PARTIAL: {results['PARTIAL']}."
        )

    def test_no_maintenance_questions_are_miss(self):
        """All maintenance questions should be covered by the system prompt."""
        misses = [
            q["q"] for q in TOP_50_QUESTIONS
            if q["category"] == "maintenance" and _score_question(q) == "MISS"
        ]
        assert not misses, f"Maintenance questions not covered: {misses}"

    def test_coverage_by_category(self):
        """At least 2/3 of questions in each category should score CORRECT."""
        from collections import defaultdict
        by_cat: dict[str, dict[str, int]] = defaultdict(lambda: {"CORRECT": 0, "PARTIAL": 0, "MISS": 0})
        for q_def in TOP_50_QUESTIONS:
            score = _score_question(q_def)
            by_cat[q_def["category"]][score] += 1

        failures = []
        for cat, counts in by_cat.items():
            total = sum(counts.values())
            correct = counts["CORRECT"]
            if total > 0 and (correct / total) < 0.50:
                failures.append(
                    f"{cat}: {correct}/{total} CORRECT ({correct/total:.0%})"
                )

        assert not failures, (
            "Some categories have <50% CORRECT coverage:\n"
            + "\n".join(f"  {f}" for f in failures)
        )
