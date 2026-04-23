"""
Integration tests for AcceptInviteView (GET + POST).

Covers:
  - Happy path: GET pre-fills email; POST creates user, returns JWT tokens
  - Expired (already-accepted) invite → 400
  - Cancelled invite → 410
  - Unknown / invalid token → 400

Run with:
    cd backend && pytest apps/accounts/tests/test_invite_accept.py -v
"""
import uuid
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserInvite


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def _make_inviter():
    return User.objects.create_user(
        email="agent@example.com",
        password="agentpass",
        role=User.Role.AGENT,
    )


def _make_invite(inviter, email="tenant@example.com", role="tenant", **kwargs):
    return UserInvite.objects.create(
        email=email,
        role=role,
        invited_by=inviter,
        **kwargs,
    )


ACCEPT_URL = "/api/v1/auth/accept-invite/"


# ─────────────────────────────────────────────────────────────────
# GET: token lookup
# ─────────────────────────────────────────────────────────────────

class AcceptInviteGetTests(APITestCase):

    def setUp(self):
        self.inviter = _make_inviter()

    def test_get_valid_token_returns_email_and_role(self):
        invite = _make_invite(self.inviter)
        resp = self.client.get(ACCEPT_URL, {"token": str(invite.token)})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["email"], "tenant@example.com")
        self.assertEqual(resp.data["role"], "tenant")

    def test_get_unknown_token_returns_400(self):
        resp = self.client.get(ACCEPT_URL, {"token": str(uuid.uuid4())})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_invalid_token_string_returns_400(self):
        resp = self.client.get(ACCEPT_URL, {"token": "not-a-uuid"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_missing_token_returns_400(self):
        resp = self.client.get(ACCEPT_URL)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_cancelled_invite_returns_410(self):
        invite = _make_invite(self.inviter, cancelled_at=timezone.now())
        resp = self.client.get(ACCEPT_URL, {"token": str(invite.token)})
        self.assertEqual(resp.status_code, status.HTTP_410_GONE)
        self.assertEqual(resp.data["detail"], "invite_cancelled")

    def test_get_already_accepted_invite_returns_400(self):
        invite = _make_invite(self.inviter, accepted_at=timezone.now())
        resp = self.client.get(ACCEPT_URL, {"token": str(invite.token)})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already been used", resp.data["detail"])


# ─────────────────────────────────────────────────────────────────
# POST: happy path
# ─────────────────────────────────────────────────────────────────

class AcceptInvitePostHappyPathTests(APITestCase):

    def setUp(self):
        self.inviter = _make_inviter()
        self.invite = _make_invite(self.inviter)

    def test_post_creates_user_and_returns_jwt(self):
        payload = {
            "token": str(self.invite.token),
            "first_name": "Jane",
            "last_name": "Smith",
            "password": "SecurePass123!",
        }
        resp = self.client.post(ACCEPT_URL, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        # JWT tokens present
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)

        # User created with correct email + role
        user = User.objects.get(email="tenant@example.com")
        self.assertEqual(user.first_name, "Jane")
        self.assertEqual(user.last_name, "Smith")
        self.assertEqual(user.role, "tenant")

        # Invite marked accepted
        self.invite.refresh_from_db()
        self.assertIsNotNone(self.invite.accepted_at)

    def test_post_marks_invite_accepted(self):
        payload = {
            "token": str(self.invite.token),
            "first_name": "Bob",
            "last_name": "Jones",
            "password": "AnotherPass456!",
        }
        self.client.post(ACCEPT_URL, payload, format="json")
        self.invite.refresh_from_db()
        self.assertIsNotNone(self.invite.accepted_at)


# ─────────────────────────────────────────────────────────────────
# POST: error paths
# ─────────────────────────────────────────────────────────────────

class AcceptInvitePostErrorTests(APITestCase):

    def setUp(self):
        self.inviter = _make_inviter()

    def test_post_already_accepted_invite_returns_400(self):
        invite = _make_invite(self.inviter, accepted_at=timezone.now())
        payload = {
            "token": str(invite.token),
            "first_name": "X",
            "last_name": "Y",
            "password": "ValidPass123!",
        }
        resp = self.client.post(ACCEPT_URL, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_unknown_token_returns_400(self):
        payload = {
            "token": str(uuid.uuid4()),
            "first_name": "X",
            "last_name": "Y",
            "password": "ValidPass123!",
        }
        resp = self.client.post(ACCEPT_URL, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_missing_password_returns_400(self):
        invite = _make_invite(self.inviter, email="nopwd@example.com")
        payload = {
            "token": str(invite.token),
            "first_name": "A",
            "last_name": "B",
        }
        resp = self.client.post(ACCEPT_URL, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_weak_password_returns_400(self):
        invite = _make_invite(self.inviter, email="weak@example.com")
        payload = {
            "token": str(invite.token),
            "first_name": "A",
            "last_name": "B",
            "password": "123",
        }
        resp = self.client.post(ACCEPT_URL, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
