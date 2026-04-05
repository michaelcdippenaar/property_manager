"""Unit tests for accounts serializers — validate field rules without DB hits."""
import pytest
from unittest.mock import patch, MagicMock

pytestmark = pytest.mark.unit


class TestRegisterSerializer:

    @pytest.mark.green
    def test_password_field_has_min_length_8(self):
        """RegisterSerializer.password has min_length=8 declared on the field."""
        from apps.accounts.serializers import RegisterSerializer
        field = RegisterSerializer().fields["password"]
        assert field.min_length == 8

    @pytest.mark.green
    def test_email_field_is_required(self):
        from apps.accounts.serializers import RegisterSerializer
        field = RegisterSerializer().fields["email"]
        assert field.required is True

    @pytest.mark.green
    def test_password_field_is_write_only(self):
        from apps.accounts.serializers import RegisterSerializer
        field = RegisterSerializer().fields["password"]
        assert field.write_only is True

    @pytest.mark.green
    def test_invalid_email_format_raises_validation_error(self):
        """
        Passes invalid email — expects serializer.is_valid() to be False.
        Marked red: depends on DB check (User.objects.filter) in validate_email,
        which will fail without a proper Django test setup.
        Use integration tests for full validation flow.
        """
        from apps.accounts.serializers import RegisterSerializer
        data = {"email": "not-an-email", "password": "ValidPass1"}
        with patch("apps.accounts.serializers.User.objects") as mock_qs:
            mock_qs.filter.return_value.exists.return_value = False
            s = RegisterSerializer(data=data)
            assert s.is_valid() is False
            assert "email" in s.errors

    @pytest.mark.green
    def test_short_password_fails_validation(self):
        """
        min_length=8 should reject passwords shorter than 8 chars.
        Marked red: validate_password also calls Django's AUTH_PASSWORD_VALIDATORS
        which require Django settings to be configured.
        """
        from apps.accounts.serializers import RegisterSerializer
        data = {"email": "valid@example.com", "password": "abc"}
        with patch("apps.accounts.serializers.User.objects") as mock_qs:
            mock_qs.filter.return_value.exists.return_value = False
            s = RegisterSerializer(data=data)
            assert s.is_valid() is False
            assert "password" in s.errors


class TestLoginSerializer:

    @pytest.mark.green
    def test_email_field_is_required(self):
        from apps.accounts.serializers import LoginSerializer
        field = LoginSerializer().fields["email"]
        assert field.required is True

    @pytest.mark.green
    def test_password_field_is_required(self):
        from apps.accounts.serializers import LoginSerializer
        field = LoginSerializer().fields["password"]
        assert field.required is True

    @pytest.mark.green
    def test_password_field_is_write_only(self):
        from apps.accounts.serializers import LoginSerializer
        field = LoginSerializer().fields["password"]
        assert field.write_only is True


class TestUserSerializer:

    @pytest.mark.green
    def test_role_is_read_only(self):
        """After auth hardening, role must be in read_only_fields."""
        from apps.accounts.serializers import UserSerializer
        assert "role" in UserSerializer.Meta.read_only_fields

    @pytest.mark.green
    def test_email_is_read_only(self):
        """email must be in read_only_fields to prevent self-modification."""
        from apps.accounts.serializers import UserSerializer
        assert "email" in UserSerializer.Meta.read_only_fields

    @pytest.mark.green
    def test_full_name_is_read_only(self):
        from apps.accounts.serializers import UserSerializer
        field = UserSerializer().fields["full_name"]
        assert field.read_only is True

    @pytest.mark.green
    def test_expected_fields_present(self):
        from apps.accounts.serializers import UserSerializer
        fields = set(UserSerializer().fields.keys())
        expected = {"id", "email", "first_name", "last_name", "full_name", "phone", "role", "date_joined"}
        assert expected.issubset(fields)


class TestPersonSerializer:

    @pytest.mark.green
    def test_full_name_field_is_required(self):
        """Person.full_name has no blank=True, so the serializer should require it."""
        from apps.accounts.serializers import PersonSerializer
        field = PersonSerializer().fields["full_name"]
        assert field.required is True

    @pytest.mark.green
    def test_id_is_read_only(self):
        from apps.accounts.serializers import PersonSerializer
        assert "id" in PersonSerializer.Meta.read_only_fields

    @pytest.mark.green
    def test_created_at_is_read_only(self):
        from apps.accounts.serializers import PersonSerializer
        assert "created_at" in PersonSerializer.Meta.read_only_fields

    @pytest.mark.green
    def test_expected_fields_include_company_fields(self):
        from apps.accounts.serializers import PersonSerializer
        fields = set(PersonSerializer().fields.keys())
        assert "company_reg" in fields
        assert "vat_number" in fields
        assert "person_type" in fields


class TestInviteUserSerializer:

    @pytest.mark.green
    def test_email_is_required(self):
        from apps.accounts.serializers import InviteUserSerializer
        field = InviteUserSerializer().fields["email"]
        assert field.required is True

    @pytest.mark.green
    def test_role_is_required(self):
        from apps.accounts.serializers import InviteUserSerializer
        field = InviteUserSerializer().fields["role"]
        assert field.required is True

    @pytest.mark.green
    def test_role_choices_match_user_roles(self):
        from apps.accounts.serializers import InviteUserSerializer
        from apps.accounts.models import User
        field = InviteUserSerializer().fields["role"]
        serializer_choices = set(c[0] for c in field.choices.items())
        user_role_values = {r[0] for r in User.Role.choices}
        assert serializer_choices == user_role_values
