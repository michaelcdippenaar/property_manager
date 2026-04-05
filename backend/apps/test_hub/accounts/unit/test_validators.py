"""Unit tests for accounts validators and throttles — no DB required."""
import pytest
from django.core.exceptions import ValidationError

pytestmark = pytest.mark.unit


class TestComplexityValidator:

    @pytest.mark.green
    def test_valid_password_passes(self):
        """A password with upper, lower, and digit passes."""
        from apps.accounts.validators import ComplexityValidator
        v = ComplexityValidator()
        # Should not raise
        v.validate("StrongPass1")

    @pytest.mark.green
    def test_all_lowercase_fails(self):
        """Password without uppercase should raise ValidationError."""
        from apps.accounts.validators import ComplexityValidator
        v = ComplexityValidator()
        with pytest.raises(ValidationError) as exc_info:
            v.validate("alllowercase1")
        assert "uppercase" in str(exc_info.value).lower()

    @pytest.mark.green
    def test_all_uppercase_fails(self):
        """Password without lowercase should raise ValidationError."""
        from apps.accounts.validators import ComplexityValidator
        v = ComplexityValidator()
        with pytest.raises(ValidationError) as exc_info:
            v.validate("ALLUPPERCASE1")
        assert "lowercase" in str(exc_info.value).lower()

    @pytest.mark.green
    def test_no_digit_fails(self):
        """Password without a digit should raise ValidationError."""
        from apps.accounts.validators import ComplexityValidator
        v = ComplexityValidator()
        with pytest.raises(ValidationError) as exc_info:
            v.validate("NoDigitsHere")
        assert "digit" in str(exc_info.value).lower()

    @pytest.mark.green
    def test_get_help_text_is_non_empty_string(self):
        from apps.accounts.validators import ComplexityValidator
        v = ComplexityValidator()
        text = v.get_help_text()
        assert isinstance(text, str)
        assert len(text) > 0

    @pytest.mark.green
    def test_get_help_text_mentions_all_requirements(self):
        from apps.accounts.validators import ComplexityValidator
        v = ComplexityValidator()
        text = v.get_help_text().lower()
        assert "uppercase" in text
        assert "lowercase" in text
        assert "digit" in text

    @pytest.mark.green
    def test_boundary_single_char_each_type(self):
        """Exactly one of each required character type passes."""
        from apps.accounts.validators import ComplexityValidator
        v = ComplexityValidator()
        # A1b — has uppercase (A), digit (1), lowercase (b)
        v.validate("A1b")

    @pytest.mark.green
    def test_empty_password_fails_on_uppercase(self):
        from apps.accounts.validators import ComplexityValidator
        v = ComplexityValidator()
        with pytest.raises(ValidationError):
            v.validate("")
