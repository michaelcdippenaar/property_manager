"""
Unit tests for apps.ai.scrubber -- POPIA s72 PII redaction.

Run with:
    cd backend && pytest apps/ai/tests/test_pii_scrubber.py -v
"""
import pytest

from apps.ai.scrubber import scrub


# ---------------------------------------------------------------------------
# SA ID number tests (13-digit)
# ---------------------------------------------------------------------------

class TestSAIDNumber:
    """South African ID number -- 13 consecutive digits."""

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
        # 14 digits -- should NOT match the 13-digit SA ID pattern (word
        # boundary), and the bank account pattern requires a context cue
        # so a solid 14-digit string without context is left untouched.
        result = scrub("ref: 12345678901234")
        assert result.count("[REDACTED]") == 0

    def test_empty_string_unchanged(self):
        assert scrub("") == ""

    def test_none_like_empty_unchanged(self):
        assert scrub("   ") == "   "


# ---------------------------------------------------------------------------
# Bank account number tests (context-gated 8-11 digits)
# ---------------------------------------------------------------------------

class TestBankAccountNumber:
    """SA bank account numbers -- 8 to 11 digits with a banking context cue."""

    def test_account_keyword_before_digits_redacted(self):
        result = scrub("account 1234567890")
        assert "1234567890" not in result
        assert "[REDACTED]" in result

    def test_acct_keyword_before_digits_redacted(self):
        result = scrub("acct 62345678")
        assert "62345678" not in result
        assert "[REDACTED]" in result

    def test_bank_account_keyword_redacted(self):
        result = scrub("bank account 12345678")
        assert "12345678" not in result
        assert "[REDACTED]" in result

    def test_eft_account_keyword_redacted(self):
        result = scrub("Please EFT to account 9876543210 at FNB")
        assert "9876543210" not in result
        assert "[REDACTED]" in result

    def test_iban_keyword_redacted(self):
        result = scrub("IBAN 12345678901")
        assert "12345678901" not in result
        assert "[REDACTED]" in result

    def test_account_with_colon_separator_redacted(self):
        result = scrub("Account: 62345678")
        assert "62345678" not in result
        assert "[REDACTED]" in result

    def test_account_with_hash_separator_redacted(self):
        result = scrub("Account #87654321")
        assert "87654321" not in result
        assert "[REDACTED]" in result

    def test_5_digit_number_not_redacted(self):
        # 5 digits is below the 8-digit minimum -- not redacted even with context
        result = scrub("unit 12345 on floor 2")
        assert "12345" in result

    def test_isolated_8_digit_no_context_not_redacted(self):
        # Without a banking cue, isolated 8-digit sequences are NOT redacted
        result = scrub("ref 62345678 for your records")
        assert "62345678" in result
        assert "[REDACTED]" not in result

    def test_multiple_pii_types_in_one_message(self):
        text = "ID 9001015009087 passport A98765432 account 62345678"
        result = scrub(text)
        assert "9001015009087" not in result
        assert "A98765432" not in result
        assert "62345678" not in result
        assert result.count("[REDACTED]") == 3


# ---------------------------------------------------------------------------
# Passport number tests
# ---------------------------------------------------------------------------

class TestPassportNumber:
    """Passport numbers -- SA format (A + 8 digits) and generic foreign."""

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
# False-positive / no-scrub tests (RNT-QUAL-057)
# ---------------------------------------------------------------------------

class TestNoFalsePositives:
    """Normal conversational text and non-PII numbers must not be mangled."""

    def test_normal_navigation_request(self):
        text = "Show me the properties list"
        assert scrub(text) == text

    def test_short_numbers_in_text(self):
        text = "I have 3 units and need to check 45 issues"
        assert scrub(text) == text

    def test_rand_amount_R_prefix_not_redacted(self):
        # "R150000" -- rand amount must not be redacted (RNT-QUAL-057)
        result = scrub("Pay R150000 deposit")
        assert "R150000" in result
        assert "[REDACTED]" not in result

    def test_rand_amount_R_with_space_not_redacted(self):
        result = scrub("Rent is R 12 345.67 per month")
        assert "[REDACTED]" not in result

    def test_rand_amount_R_with_commas_not_redacted(self):
        result = scrub("Value: R12,345")
        assert "R12,345" in result
        assert "[REDACTED]" not in result

    def test_rand_amount_ZAR_not_redacted(self):
        result = scrub("Total ZAR 150000")
        assert "150000" in result
        assert "[REDACTED]" not in result

    def test_yyyymmdd_date_not_redacted(self):
        # 8-digit YYYYMMDD date must NOT be redacted (RNT-QUAL-057)
        result = scrub("lease started 20241215")
        assert "20241215" in result
        assert "[REDACTED]" not in result

    def test_yyyymmdd_date_2026_not_redacted(self):
        result = scrub("signed on 20260424")
        assert "20260424" in result
        assert "[REDACTED]" not in result

    def test_meter_reading_kwh_not_redacted(self):
        # RNT-QUAL-057 AC: "meter reading 458790 kWh" not redacted
        result = scrub("meter reading 458790 kWh")
        assert "458790" in result
        assert "[REDACTED]" not in result

    def test_unit_suffix_km_not_redacted(self):
        result = scrub("distance 12345678 km")
        assert "12345678" in result
        assert "[REDACTED]" not in result

    def test_unit_suffix_mb_not_redacted(self):
        result = scrub("file size 10240000 MB")
        assert "10240000" in result
        assert "[REDACTED]" not in result

    def test_rand_amount_not_redacted_short(self):
        # "R1500" -- short rand amount, also cannot match passport pattern
        result = scrub("Pay R1500 rent")
        assert "R1500" in result

    def test_long_descriptive_message(self):
        text = "My geyser burst and I need urgent maintenance please help"
        assert scrub(text) == text
