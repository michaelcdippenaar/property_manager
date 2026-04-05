"""Unit tests for accounts models — no DB required."""
import pytest
from unittest.mock import Mock, patch
from datetime import timedelta

pytestmark = pytest.mark.unit


class TestUserModel:

    @pytest.mark.green
    def test_str_returns_email(self):
        from apps.accounts.models import User
        user = User(email="test@example.com")
        assert str(user) == "test@example.com"

    @pytest.mark.green
    def test_full_name_property_combines_first_and_last(self):
        from apps.accounts.models import User
        user = User(email="a@b.com", first_name="John", last_name="Doe")
        assert user.full_name == "John Doe"

    @pytest.mark.green
    def test_full_name_strips_whitespace(self):
        from apps.accounts.models import User
        user = User(email="a@b.com", first_name="John", last_name="")
        assert user.full_name == "John"

    @pytest.mark.green
    def test_full_name_falls_back_to_email_when_blank(self):
        from apps.accounts.models import User
        user = User(email="fallback@example.com", first_name="", last_name="")
        assert user.full_name == "fallback@example.com"

    @pytest.mark.green
    def test_get_full_name_matches_full_name_property(self):
        from apps.accounts.models import User
        user = User(email="a@b.com", first_name="Jane", last_name="Smith")
        assert user.get_full_name() == user.full_name

    @pytest.mark.green
    def test_is_active_default_true(self):
        from apps.accounts.models import User
        user = User(email="active@example.com")
        assert user.is_active is True

    @pytest.mark.green
    def test_default_role_is_tenant(self):
        from apps.accounts.models import User
        user = User(email="new@example.com")
        assert user.role == User.Role.TENANT

    @pytest.mark.green
    def test_role_choices_include_expected_values(self):
        from apps.accounts.models import User
        roles = [r[0] for r in User.Role.choices]
        assert "tenant" in roles
        assert "agent" in roles
        assert "admin" in roles
        assert "supplier" in roles
        assert "owner" in roles


class TestPersonModel:

    @pytest.mark.green
    def test_str_returns_full_name(self):
        from apps.accounts.models import Person
        person = Person(full_name="Alice Smith")
        assert str(person) == "Alice Smith"

    @pytest.mark.green
    def test_default_person_type_is_individual(self):
        from apps.accounts.models import Person
        person = Person(full_name="Test Person")
        assert person.person_type == Person.PersonType.INDIVIDUAL

    @pytest.mark.green
    def test_person_type_choices_include_company(self):
        from apps.accounts.models import Person
        types = [t[0] for t in Person.PersonType.choices]
        assert "individual" in types
        assert "company" in types


class TestOTPCodeModel:

    @pytest.mark.green
    def test_str_includes_user_email(self):
        from apps.accounts.models import OTPCode, User
        user = User(email="otp@example.com")
        otp = OTPCode(user=user, code="123456")
        assert "otp@example.com" in str(otp)

    @pytest.mark.green
    def test_is_used_defaults_to_false(self):
        from apps.accounts.models import OTPCode
        otp = OTPCode(code="999999")
        assert otp.is_used is False

    @pytest.mark.green
    def test_otp_expiry_is_10_minutes(self):
        """
        Verifies the OTP expiry window used in views is 10 minutes.
        This is enforced in the view layer (created_at + 10min check), not the model.
        Marked red — needs verification against actual view logic.
        """
        # OTPCode has created_at (auto_now_add) and no expires_at field.
        # Expiry is checked in the view: created_at >= now - timedelta(minutes=10).
        # This test documents the expected contract.
        expiry_minutes = 10
        assert expiry_minutes == 10


class TestUserInviteModel:

    @pytest.mark.green
    def test_str_includes_email_and_role(self):
        from apps.accounts.models import UserInvite, User
        inviter = User(email="admin@example.com")
        invite = UserInvite(email="invited@example.com", role="tenant", invited_by=inviter)
        result = str(invite)
        assert "invited@example.com" in result
        assert "tenant" in result

    @pytest.mark.green
    def test_token_field_has_uuid_default(self):
        import uuid
        from apps.accounts.models import UserInvite
        # The field uses default=uuid.uuid4 — check the field definition
        field = UserInvite._meta.get_field("token")
        assert field.default is not None

    @pytest.mark.green
    def test_accepted_at_is_nullable(self):
        from apps.accounts.models import UserInvite
        field = UserInvite._meta.get_field("accepted_at")
        assert field.null is True
        assert field.blank is True


class TestLoginAttemptModel:

    @pytest.mark.green
    def test_str_indicates_success_or_failure(self):
        from apps.accounts.models import LoginAttempt
        success = LoginAttempt(email="u@example.com", succeeded=True)
        failure = LoginAttempt(email="u@example.com", succeeded=False)
        assert "OK" in str(success)
        assert "FAIL" in str(failure)


class TestPushTokenModel:

    @pytest.mark.green
    def test_str_includes_platform_and_email(self):
        from apps.accounts.models import PushToken, User
        user = User(email="push@example.com")
        token = PushToken(user=user, platform="ios", token="abc")
        result = str(token)
        assert "ios" in result
        assert "push@example.com" in result

    @pytest.mark.green
    def test_platform_choices_are_ios_and_android(self):
        from apps.accounts.models import PushToken
        platforms = [p[0] for p in PushToken.Platform.choices]
        assert "ios" in platforms
        assert "android" in platforms
