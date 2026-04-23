"""
Unit tests for apps.ai.scrubber — POPIA s72 PII redaction.

Run with:
    cd backend && pytest apps/ai/tests/test_pii_scrubber.py -v
"""
import pytest

from apps.ai.scrubber import scrub


# ---------------------------------------------------------------------------
# SA ID number tests (13-digit)
# ---------------------------------------------------------------------------

class TestSAIDNumber:
    """South African ID number — 13 consecutive digits."""

    def test_standalone_id_is_redacted(self):
        assert scrub("9001015009087") == "[REDACTED]"

    def test_id_in_sentence_is_redacted(self):
        result = scrub("My ID number is 9001015009087 please verify.")
        assert "9001015009087" not in result
        assert "[REDACTED]" in result

    def test_multiple_ids_are_redacted(self):
        result = scrub("IDs: 9001015009087 and 8504120033086")
        assert "9001015009087" not in result
        assert "8504120033086" not in result
        assert result.count("[REDACTED]") == 2

    def test_14_digit_number_not_redacted_as_id(self):
        # 14 digits — should NOT match the 13-digit SA ID pattern (word
        # boundary), and the bank account pattern also requires word boundaries
        # so a solid 14-digit string is left untouched.
        # The important thing is the 14-digit number is NOT matched as an ID.
        result = scrub("ref: 12345678901234")
        # 13-digit boundary check: no SA ID substitution occurred
        assert result.count("[REDACTED]") == 0

    def test_empty_string_unchanged(self):
        assert scrub("") == ""

    def test_none_like_empty_unchanged(self):
        # Edge: scrub should handle empty gracefully
        assert scrub("   ") == "   "


# ---------------------------------------------------------------------------
# Bank account number tests (6–11 digits)
# ---------------------------------------------------------------------------

class TestBankAccountNumber:
    """SA bank account numbers — 6 to 11 consecutive digits."""

    def test_6_digit_account_redacted(self):
        assert scrub("Account: 123456") == "Account: [REDACTED]"

    def test_8_digit_account_redacted(self):
        assert scrub("Pay to 62345678") == "Pay to [REDACTED]"

    def test_11_digit_account_redacted(self):
        assert scrub("acct 12345678901") == "acct [REDACTED]"

    def test_5_digit_number_not_redacted(self):
        # 5 digits is below threshold — should NOT be redacted
        result = scrub("unit 12345 on floor 2")
        assert "12345" in result

    def test_account_in_sentence(self):
        result = scrub("Please EFT to account 9876543210 at FNB")
        assert "9876543210" not in result
        assert "[REDACTED]" in result


# ---------------------------------------------------------------------------
# Passport number tests
# ---------------------------------------------------------------------------

class TestPassportNumber:
    """Passport numbers — SA format (A + 8 digits) and generic foreign."""

    def test_sa_passport_redacted(self):
        assert scrub("Passport: A12345678") == "Passport: [REDACTED]"

    def test_two_letter_prefix_passport_redacted(self):
        assert scrub("AB1234567") == "[REDACTED]"

    def test_mixed_case_passport_redacted(self):
        result = scrub("passport is a12345678")
        assert "a12345678" not in result

    def test_plain_word_not_redacted(self):
        result = scrub("Please navigate to leases")
        assert result == "Please navigate to leases"


# ---------------------------------------------------------------------------
# False-positive / no-scrub tests (normal text must pass through intact)
# ---------------------------------------------------------------------------

class TestNoFalsePositives:
    """Normal conversational text must not be mangled."""

    def test_normal_navigation_request(self):
        text = "Show me the properties list"
        assert scrub(text) == text

    def test_short_numbers_in_text(self):
        text = "I have 3 units and need to check 45 issues"
        assert scrub(text) == text

    def test_date_like_string_not_redacted(self):
        # An 8-digit date like 20241215 — 8 digits, will be caught by bank
        # account pattern. This is an accepted tradeoff documented in scrubber.py.
        # Confirming it IS redacted (conservative approach).
        result = scrub("lease started 20241215")
        assert "20241215" not in result

    def test_rand_amount_not_redacted(self):
        # "R1500" — one letter + 4 digits — too short for passport pattern
        result = scrub("Pay R1500 rent")
        assert "R1500" in result

    def test_long_descriptive_message(self):
        text = "My geyser burst and I need urgent maintenance please help"
        assert scrub(text) == text

    def test_multiple_pii_types_in_one_message(self):
        text = "ID 9001015009087 passport A98765432 account 62345678"
        result = scrub(text)
        assert "9001015009087" not in result
        assert "A98765432" not in result
        assert "62345678" not in result
        assert result.count("[REDACTED]") == 3
