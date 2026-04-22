"""
Integration tests for TOTP 2FA — RNT-SEC-003

pytest backend/apps/test_hub/accounts/integration/test_2fa.py
"""
import pytest
import pyotp
from datetime import timedelta
from unittest import mock

from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User, UserTOTP, TOTPRecoveryCode, TOTP_REQUIRED_ROLES
from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration, pytest.mark.green]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _enroll_user(user: User):
    """Fully enroll a user in TOTP and return (UserTOTP, [recovery_codes])."""
    secret = pyotp.random_base32()
    totp_rec, _ = UserTOTP.objects.get_or_create(user=user, defaults={"secret": secret})
    if not totp_rec.secret:
        totp_rec.secret = secret
    totp_rec.is_active = True
    totp_rec.enrolled_at = timezone.now()
    totp_rec.grace_deadline = None
    totp_rec.save()
    codes = TOTPRecoveryCode.generate_for_user(user)
    return totp_rec, codes


def _current_code(totp_rec: UserTOTP) -> str:
    return pyotp.TOTP(totp_rec.secret).now()


# ── Login gate tests ──────────────────────────────────────────────────────────

class LoginTwoFAGateTests(TremlyAPITestCase):
    """Login with a TOTP-required role should return two_fa_required=True."""

    def test_agent_login_enrolled_returns_two_fa_token(self):
        agent = self.create_user(email="agent@test.com", password="pass12345", role="agent")
        totp_rec, _ = _enroll_user(agent)

        resp = self.client.post(reverse("auth-login"), {"email": "agent@test.com", "password": "pass12345"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data.get("two_fa_required"))
        self.assertIn("two_fa_token", resp.data)
        self.assertNotIn("access", resp.data)

    def test_tenant_login_no_totp_returns_full_tokens(self):
        """Tenant without TOTP enrolled gets full tokens — optional 2FA."""
        tenant = self.create_user(email="tenant@test.com", password="pass12345", role="tenant")

        resp = self.client.post(reverse("auth-login"), {"email": "tenant@test.com", "password": "pass12345"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)
        self.assertFalse(resp.data.get("two_fa_required", False))

    def test_agent_login_not_enrolled_in_grace_gets_access_and_enroll_flag(self):
        """Agent without TOTP enrolled but within grace period gets access + enroll_required flag."""
        agent = self.create_user(email="new_agent@test.com", password="pass12345", role="agent")

        resp = self.client.post(reverse("auth-login"), {"email": "new_agent@test.com", "password": "pass12345"})
        self.assertEqual(resp.status_code, 200)
        # Within grace period — tokens issued but enrollment flag set
        self.assertIn("access", resp.data)
        self.assertTrue(resp.data.get("two_fa_enroll_required"))
        self.assertFalse(resp.data.get("two_fa_required", False))

    def test_agent_login_not_enrolled_past_grace_hard_blocked(self):
        """Agent past grace period should be hard-blocked without tokens."""
        agent = self.create_user(email="late_agent@test.com", password="pass12345", role="agent")
        # Create an expired grace record
        past_deadline = timezone.now() - timedelta(days=1)
        UserTOTP.objects.create(user=agent, secret="", grace_deadline=past_deadline)

        resp = self.client.post(reverse("auth-login"), {"email": "late_agent@test.com", "password": "pass12345"})
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("access", resp.data)
        self.assertTrue(resp.data.get("two_fa_hard_blocked"))
        self.assertTrue(resp.data.get("two_fa_enroll_required"))

    def test_wrong_password_still_blocked(self):
        resp = self.client.post(reverse("auth-login"), {"email": "noone@test.com", "password": "wrong"})
        self.assertEqual(resp.status_code, 400)


# ── TOTP verify tests ─────────────────────────────────────────────────────────

class TOTPVerifyTests(TremlyAPITestCase):
    url = reverse("2fa-verify")

    def _partial_login(self, email, password):
        resp = self.client.post(reverse("auth-login"), {"email": email, "password": password})
        return resp.data.get("two_fa_token")

    def test_verify_correct_code_issues_full_tokens(self):
        agent = self.create_user(email="va@test.com", password="pass12345", role="agent")
        totp_rec, _ = _enroll_user(agent)
        two_fa_token = self._partial_login("va@test.com", "pass12345")
        self.assertIsNotNone(two_fa_token)

        code = _current_code(totp_rec)
        resp = self.client.post(self.url, {"two_fa_token": two_fa_token, "totp_code": code})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)

    def test_verify_wrong_code_rejected(self):
        agent = self.create_user(email="vb@test.com", password="pass12345", role="agent")
        totp_rec, _ = _enroll_user(agent)
        two_fa_token = self._partial_login("vb@test.com", "pass12345")

        resp = self.client.post(self.url, {"two_fa_token": two_fa_token, "totp_code": "000000"})
        self.assertEqual(resp.status_code, 400)

    def test_verify_missing_two_fa_token(self):
        resp = self.client.post(self.url, {"totp_code": "123456"})
        self.assertEqual(resp.status_code, 400)

    def test_verify_regular_access_token_rejected(self):
        """A plain JWT should not work as a two_fa_token."""
        agent = self.create_user(email="vc@test.com", password="pass12345", role="agent")
        tokens = self.get_tokens(agent)
        resp = self.client.post(self.url, {"two_fa_token": tokens["access"], "totp_code": "123456"})
        self.assertEqual(resp.status_code, 401)


# ── TOTP setup tests ──────────────────────────────────────────────────────────

class TOTPSetupTests(TremlyAPITestCase):
    setup_url = reverse("2fa-setup")
    confirm_url = reverse("2fa-setup-confirm")

    def test_setup_returns_secret_and_qr(self):
        agent = self.create_user(email="sa@test.com", password="pass12345", role="agent")
        self.authenticate(agent)

        resp = self.client.post(self.setup_url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("secret", resp.data)
        self.assertIn("otpauth_uri", resp.data)

    def test_setup_confirm_activates_totp_and_issues_recovery_codes(self):
        agent = self.create_user(email="sb@test.com", password="pass12345", role="agent")
        self.authenticate(agent)

        # Get setup details
        resp = self.client.post(self.setup_url)
        self.assertEqual(resp.status_code, 200)
        secret = resp.data["secret"]

        # Confirm with valid code
        code = pyotp.TOTP(secret).now()
        resp = self.client.post(self.confirm_url, {"totp_code": code})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("recovery_codes", resp.data)
        self.assertEqual(len(resp.data["recovery_codes"]), 10)

        # TOTP record should now be active
        agent.refresh_from_db()
        self.assertTrue(agent.totp.is_active)

    def test_setup_confirm_wrong_code_rejected(self):
        agent = self.create_user(email="sc@test.com", password="pass12345", role="agent")
        self.authenticate(agent)
        self.client.post(self.setup_url)
        resp = self.client.post(self.confirm_url, {"totp_code": "000000"})
        self.assertEqual(resp.status_code, 400)

    def test_setup_already_active_returns_error(self):
        agent = self.create_user(email="sd@test.com", password="pass12345", role="agent")
        _enroll_user(agent)
        self.authenticate(agent)
        resp = self.client.post(self.setup_url)
        self.assertEqual(resp.status_code, 400)

    def test_setup_no_auth_rejected(self):
        """Setup without any token or Bearer should return 401."""
        resp = self.client.post(self.setup_url)
        self.assertEqual(resp.status_code, 401)

    def test_setup_confirm_no_auth_rejected(self):
        """Confirm without any token or Bearer should return 401."""
        resp = self.client.post(self.confirm_url, {"totp_code": "123456"})
        self.assertEqual(resp.status_code, 401)


# ── Hard-blocked enrollment via two_fa_token tests ───────────────────────────

class HardBlockedEnrollmentTests(TremlyAPITestCase):
    """
    Regression test for the blocker raised in review: when grace period has
    expired the login response withholds access/refresh tokens and only returns
    a ``two_fa_token``.  The setup endpoints must accept that token so the user
    can still enroll.
    """
    setup_url = reverse("2fa-setup")
    confirm_url = reverse("2fa-setup-confirm")

    def _hard_blocked_login(self, email, password):
        """Login and return the two_fa_token for a hard-blocked user."""
        resp = self.client.post(reverse("auth-login"), {"email": email, "password": password})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data.get("two_fa_hard_blocked"), "Expected hard_blocked in response")
        self.assertNotIn("access", resp.data, "Hard-blocked user must not receive access token")
        return resp.data.get("two_fa_token")

    def test_hard_blocked_user_can_setup_via_two_fa_token(self):
        """Hard-blocked user (grace expired) can reach /auth/2fa/setup/ using two_fa_token."""
        agent = self.create_user(email="hb_setup@test.com", password="pass12345", role="agent")
        # Expire the grace period
        past_deadline = timezone.now() - timedelta(days=1)
        UserTOTP.objects.create(user=agent, secret="", grace_deadline=past_deadline)

        two_fa_token = self._hard_blocked_login("hb_setup@test.com", "pass12345")
        self.assertIsNotNone(two_fa_token)

        resp = self.client.post(self.setup_url, {"two_fa_token": two_fa_token})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("secret", resp.data)
        self.assertIn("otpauth_uri", resp.data)

    def test_hard_blocked_user_can_complete_enrollment_via_two_fa_token(self):
        """Hard-blocked user can call setup + confirm using only the two_fa_token."""
        agent = self.create_user(email="hb_confirm@test.com", password="pass12345", role="agent")
        past_deadline = timezone.now() - timedelta(days=1)
        UserTOTP.objects.create(user=agent, secret="", grace_deadline=past_deadline)

        two_fa_token = self._hard_blocked_login("hb_confirm@test.com", "pass12345")
        self.assertIsNotNone(two_fa_token)

        # Step 1: get the secret via setup
        resp = self.client.post(self.setup_url, {"two_fa_token": two_fa_token})
        self.assertEqual(resp.status_code, 200)
        secret = resp.data["secret"]

        # Step 2: confirm with a valid TOTP code
        code = pyotp.TOTP(secret).now()
        resp = self.client.post(self.confirm_url, {"two_fa_token": two_fa_token, "totp_code": code})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("recovery_codes", resp.data)
        self.assertEqual(len(resp.data["recovery_codes"]), 10)

        # TOTP record should now be active and enrollment is complete
        agent.refresh_from_db()
        self.assertTrue(agent.totp.is_active)

    def test_hard_blocked_setup_with_regular_access_token_rejected(self):
        """A plain Bearer access token must not be treated as a two_fa_token."""
        agent = self.create_user(email="hb_plain@test.com", password="pass12345", role="agent")
        past_deadline = timezone.now() - timedelta(days=1)
        UserTOTP.objects.create(user=agent, secret="", grace_deadline=past_deadline)

        # Obtain a regular access token directly (bypassing the login gate)
        tokens = self.get_tokens(agent)
        resp = self.client.post(self.setup_url, {"two_fa_token": tokens["access"]})
        self.assertEqual(resp.status_code, 401)

    def test_in_grace_user_can_setup_via_two_fa_token(self):
        """
        In-grace users receive both an access token AND a two_fa_token.  Both
        paths must work.  This test confirms the two_fa_token path also succeeds
        (for consistent frontend code across both states).
        """
        agent = self.create_user(email="ig_setup@test.com", password="pass12345", role="agent")

        resp = self.client.post(reverse("auth-login"), {"email": "ig_setup@test.com", "password": "pass12345"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data.get("two_fa_enroll_required"))
        # In-grace: access token IS present
        self.assertIn("access", resp.data)
        two_fa_token = resp.data.get("two_fa_token")
        self.assertIsNotNone(two_fa_token)

        # Use two_fa_token path for setup (frontend can use this consistently)
        resp = self.client.post(self.setup_url, {"two_fa_token": two_fa_token})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("secret", resp.data)


# ── Recovery code tests ───────────────────────────────────────────────────────

class TOTPRecoveryTests(TremlyAPITestCase):
    url = reverse("2fa-recovery")

    def _partial_login(self, email, password):
        resp = self.client.post(reverse("auth-login"), {"email": email, "password": password})
        return resp.data.get("two_fa_token")

    def test_valid_recovery_code_issues_full_tokens(self):
        agent = self.create_user(email="ra@test.com", password="pass12345", role="agent")
        totp_rec, plain_codes = _enroll_user(agent)
        two_fa_token = self._partial_login("ra@test.com", "pass12345")

        resp = self.client.post(self.url, {
            "two_fa_token": two_fa_token,
            "recovery_code": plain_codes[0],
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)

    def test_reuse_recovery_code_rejected(self):
        agent = self.create_user(email="rb@test.com", password="pass12345", role="agent")
        totp_rec, plain_codes = _enroll_user(agent)
        two_fa_token = self._partial_login("rb@test.com", "pass12345")

        self.client.post(self.url, {"two_fa_token": two_fa_token, "recovery_code": plain_codes[0]})
        # Re-login for fresh token
        two_fa_token2 = self._partial_login("rb@test.com", "pass12345")
        resp = self.client.post(self.url, {"two_fa_token": two_fa_token2, "recovery_code": plain_codes[0]})
        self.assertEqual(resp.status_code, 400)

    def test_invalid_recovery_code_rejected(self):
        agent = self.create_user(email="rc@test.com", password="pass12345", role="agent")
        totp_rec, _ = _enroll_user(agent)
        two_fa_token = self._partial_login("rc@test.com", "pass12345")
        resp = self.client.post(self.url, {"two_fa_token": two_fa_token, "recovery_code": "XXXX-XXXX-XXXX"})
        self.assertEqual(resp.status_code, 400)


# ── Status tests ──────────────────────────────────────────────────────────────

class TOTPStatusTests(TremlyAPITestCase):
    url = reverse("2fa-status")

    def test_not_enrolled_agent_shows_required_unenrolled(self):
        agent = self.create_user(email="sta@test.com", password="pass12345", role="agent")
        self.authenticate(agent)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["required"])
        self.assertFalse(resp.data["enrolled"])

    def test_enrolled_agent_shows_enrolled(self):
        agent = self.create_user(email="stb@test.com", password="pass12345", role="agent")
        _enroll_user(agent)
        self.authenticate(agent)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["enrolled"])

    def test_tenant_shows_not_required(self):
        tenant = self.create_user(email="stc@test.com", password="pass12345", role="tenant")
        self.authenticate(tenant)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data["required"])


# ── Recovery code model unit tests ────────────────────────────────────────────

class RecoveryCodeModelTests(TremlyAPITestCase):

    def test_generate_creates_10_codes(self):
        user = self.create_user(email="m1@test.com", role="agent")
        codes = TOTPRecoveryCode.generate_for_user(user, count=10)
        self.assertEqual(len(codes), 10)
        self.assertEqual(TOTPRecoveryCode.objects.filter(user=user).count(), 10)

    def test_redeem_valid_code_succeeds(self):
        user = self.create_user(email="m2@test.com", role="agent")
        codes = TOTPRecoveryCode.generate_for_user(user)
        result = TOTPRecoveryCode.redeem(user, codes[0])
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.used_at)

    def test_redeem_invalid_code_fails(self):
        user = self.create_user(email="m3@test.com", role="agent")
        TOTPRecoveryCode.generate_for_user(user)
        result = TOTPRecoveryCode.redeem(user, "FAKE-FAKE-FAKE")
        self.assertIsNone(result)

    def test_regenerate_invalidates_old_codes(self):
        user = self.create_user(email="m4@test.com", role="agent")
        old_codes = TOTPRecoveryCode.generate_for_user(user)
        TOTPRecoveryCode.generate_for_user(user)
        # Old codes no longer valid
        result = TOTPRecoveryCode.redeem(user, old_codes[0])
        self.assertIsNone(result)
