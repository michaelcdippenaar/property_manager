"""
Integration tests for AcceptInviteView (GET + POST) and invite URL generation.

Covers:
  - Happy path: GET pre-fills email; POST creates user, returns JWT tokens
  - Expired (already-accepted) invite → 400
  - Cancelled invite → 410
  - Unknown / invalid token → 400
  - URL-by-role branching: tenant → /invite/<token>; others → /accept-invite?token=

Run with:
    cd backend && pytest apps/accounts/tests/test_invite_accept.py -v

xdist note
----------
These tests use Django's APITestCase (TestCase-based).  Under pytest-xdist each
worker creates its own test database; all workers in the same OS process share the
in-process ContentType._cache dict.  When a worker's DB is torn down, cached
ContentType PKs become stale — the audit signal fires on the next User.save() and
tries to INSERT an AuditEvent with a content_type_id that no longer exists in the
new DB, producing:

    IntegrityError: audit_auditevent … content_type_id … is not present in
    table "django_content_type"

The fix lives in conftest.py: the autouse _clear_contenttypes_cache fixture flushes
ContentType._cache both before and after every test, preventing cross-worker cache
poisoning without any change to the test classes themselves.
"""
import uuid
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserInvite
from apps.accounts.admin_views import _build_invite_url


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


# ─────────────────────────────────────────────────────────────────
# URL-by-role branching (_build_invite_url)
# ─────────────────────────────────────────────────────────────────

class BuildInviteUrlTests(APITestCase):
    """Unit tests for _build_invite_url — asserts the correct host/path per role."""

    def setUp(self):
        self.inviter = _make_inviter()

    @override_settings(TENANT_APP_BASE_URL="https://app.klikk.co.za")
    def test_tenant_invite_uses_tenant_app_path_param(self):
        invite = _make_invite(self.inviter, role="tenant")
        url = _build_invite_url(invite, admin_base_url="https://admin.klikk.co.za")
        self.assertEqual(url, f"https://app.klikk.co.za/invite/{invite.token}")

    @override_settings(TENANT_APP_BASE_URL="")
    def test_tenant_invite_with_empty_setting_uses_path_param(self):
        invite = _make_invite(self.inviter, role="tenant")
        url = _build_invite_url(invite, admin_base_url="https://admin.klikk.co.za")
        self.assertEqual(url, f"/invite/{invite.token}")

    def test_agent_invite_uses_admin_accept_invite_query_param(self):
        invite = _make_invite(self.inviter, role="agent")
        url = _build_invite_url(invite, admin_base_url="https://admin.klikk.co.za")
        self.assertEqual(url, f"https://admin.klikk.co.za/accept-invite?token={invite.token}")

    def test_owner_invite_uses_admin_accept_invite_query_param(self):
        invite = _make_invite(self.inviter, role="owner")
        url = _build_invite_url(invite, admin_base_url="https://admin.klikk.co.za")
        self.assertEqual(url, f"https://admin.klikk.co.za/accept-invite?token={invite.token}")

    def test_supplier_invite_uses_admin_accept_invite_query_param(self):
        invite = _make_invite(self.inviter, role="supplier")
        url = _build_invite_url(invite, admin_base_url="https://admin.klikk.co.za")
        self.assertEqual(url, f"https://admin.klikk.co.za/accept-invite?token={invite.token}")

    def test_tenant_url_contains_path_token_not_query_param(self):
        """Tenant URL must use path-param form, not ?token= query-param form."""
        invite = _make_invite(self.inviter, role="tenant")
        url = _build_invite_url(invite, admin_base_url="https://admin.klikk.co.za")
        self.assertIn(f"/invite/{invite.token}", url)
        self.assertNotIn("?token=", url)

    def test_non_tenant_url_contains_query_param_not_path_segment(self):
        """Non-tenant URLs must use ?token= form, not /invite/<token> path form."""
        invite = _make_invite(self.inviter, role="agent")
        url = _build_invite_url(invite, admin_base_url="https://admin.klikk.co.za")
        self.assertIn(f"?token={invite.token}", url)
        self.assertNotIn("/invite/", url)
