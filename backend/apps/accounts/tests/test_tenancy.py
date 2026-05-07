"""
Tenancy scaffolding tests — Phase 0 of multi-tenant rollout.

Covers:
  - Thread-local context lifecycle (set / clear / nest)
  - ``override()`` context manager (specific agency, bypass, restoration)
  - ``TenantManager`` scoping (filters by current agency, returns ``none()``
    when no agency is set, full table when bypass is active)
  - ``TenantContextMiddleware`` (populates context from ``request.user``,
    clears after response, isolates between requests)

Run:
    pytest backend/apps/accounts/tests/test_tenancy.py -v
"""
from __future__ import annotations

import threading

import pytest
from django.contrib.auth.models import AnonymousUser
from django.db import models
from django.test import RequestFactory, TestCase

from apps.accounts.models import Agency, User
from apps.accounts.tenancy import (
    TenantContextMiddleware,
    TenantManager,
    _EMPTY_CTX,
    _local,
    current_agency_id,
    is_bypass_active,
    override,
    tenant_context_for_task,
)


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────


def _reset_local():
    """Ensure no test starts with leaked context from a previous one."""
    if hasattr(_local, "tenant_ctx"):
        delattr(_local, "tenant_ctx")


def _make_agency(name: str) -> Agency:
    return Agency.objects.create(name=name)


def _make_user(email: str, agency: Agency | None = None) -> User:
    u = User.objects.create_user(email=email, password="pass")
    if agency:
        u.agency = agency
        u.save(update_fields=["agency"])
    return u


# ─────────────────────────────────────────────────────────────────
# Thread-local + helpers
# ─────────────────────────────────────────────────────────────────


class TenantContextHelpersTest(TestCase):
    def setUp(self):
        _reset_local()

    def test_default_context_is_empty(self):
        self.assertIsNone(current_agency_id())
        self.assertFalse(is_bypass_active())

    def test_override_sets_and_restores(self):
        self.assertIsNone(current_agency_id())
        with override(agency_id=99):
            self.assertEqual(current_agency_id(), 99)
            self.assertFalse(is_bypass_active())
        self.assertIsNone(current_agency_id())

    def test_override_bypass_flag(self):
        with override(bypass=True):
            self.assertTrue(is_bypass_active())
            self.assertIsNone(current_agency_id())
        self.assertFalse(is_bypass_active())

    def test_override_nests_correctly(self):
        with override(agency_id=1):
            self.assertEqual(current_agency_id(), 1)
            with override(agency_id=2):
                self.assertEqual(current_agency_id(), 2)
            # Inner exit restores agency 1, not the empty default
            self.assertEqual(current_agency_id(), 1)
        self.assertIsNone(current_agency_id())

    def test_override_restores_on_exception(self):
        with self.assertRaises(RuntimeError):
            with override(agency_id=42):
                self.assertEqual(current_agency_id(), 42)
                raise RuntimeError("boom")
        # Context cleaned up despite the exception
        self.assertIsNone(current_agency_id())

    def test_tenant_context_for_task_sets_and_restores(self):
        """QA-round-5 bug 3: task helper round-trips agency_id correctly.

        Accepts raw int agency_id, an Agency instance (via .pk), and None
        (no-op). Restores the previous context on exit, even when raised.
        """
        # Raw int
        self.assertIsNone(current_agency_id())
        with tenant_context_for_task(77):
            self.assertEqual(current_agency_id(), 77)
        self.assertIsNone(current_agency_id())

        # Object with .pk attribute
        class _AgencyLike:
            pk = 123
        with tenant_context_for_task(_AgencyLike()):
            self.assertEqual(current_agency_id(), 123)
        self.assertIsNone(current_agency_id())

        # None argument → context manager is a no-op (still cleans up)
        with tenant_context_for_task(None):
            self.assertIsNone(current_agency_id())
        self.assertIsNone(current_agency_id())

        # Restore on exception
        with self.assertRaises(RuntimeError):
            with tenant_context_for_task(55):
                self.assertEqual(current_agency_id(), 55)
                raise RuntimeError("boom")
        self.assertIsNone(current_agency_id())

    def test_thread_local_isolation(self):
        """Two threads must not see each other's tenant context."""
        results: dict[str, int | None] = {}

        def worker(name: str, agency_id: int):
            with override(agency_id=agency_id):
                # Yield briefly so the scheduler can interleave threads
                import time
                time.sleep(0.01)
                results[name] = current_agency_id()

        t1 = threading.Thread(target=worker, args=("a", 100))
        t2 = threading.Thread(target=worker, args=("b", 200))
        t1.start(); t2.start()
        t1.join(); t2.join()

        self.assertEqual(results["a"], 100)
        self.assertEqual(results["b"], 200)
        # Main thread context unchanged
        self.assertIsNone(current_agency_id())


# ─────────────────────────────────────────────────────────────────
# TenantManager
# ─────────────────────────────────────────────────────────────────


class TenantManagerTest(TestCase):
    """
    Use the existing User model (it has agency_id) as a stand-in for an
    arbitrary tenant-scoped model. We attach a TenantManager via setUpClass
    so we don't have to introduce a new test-only model + migration here.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Bolt a TenantManager onto User just for these tests.
        cls._original_objects = User.objects
        # Swap class-level managers so we can use User.tenant_objects in
        # assertions without a migration. Restored in tearDownClass.
        User.add_to_class("tenant_objects", TenantManager())

    @classmethod
    def tearDownClass(cls):
        # Pop the tenant_objects we added so other test files aren't surprised
        try:
            del User.tenant_objects
        except AttributeError:
            pass
        super().tearDownClass()

    def setUp(self):
        _reset_local()
        self.a = _make_agency("Agency A")
        self.b = _make_agency("Agency B")
        self.user_a = _make_user("a@test.com", agency=self.a)
        self.user_b = _make_user("b@test.com", agency=self.b)

    def test_no_context_returns_empty(self):
        """Without an agency context, scoped queries return nothing.

        This is the 'safe default' that prevents accidental leaks from
        misconfigured management commands or signal handlers.
        """
        self.assertEqual(User.tenant_objects.count(), 0)

    def test_scoped_to_current_agency(self):
        with override(agency_id=self.a.id):
            qs = User.tenant_objects.all()
            self.assertEqual(qs.count(), 1)
            self.assertEqual(qs.first(), self.user_a)

    def test_scoped_to_other_agency(self):
        with override(agency_id=self.b.id):
            qs = User.tenant_objects.all()
            self.assertEqual(qs.count(), 1)
            self.assertEqual(qs.first(), self.user_b)

    def test_bypass_returns_full_table(self):
        with override(bypass=True):
            self.assertGreaterEqual(User.tenant_objects.count(), 2)

    def test_unscoped_objects_always_full_table(self):
        """The unscoped manager (default ``objects``) ignores tenant context."""
        with override(agency_id=self.a.id):
            self.assertGreaterEqual(User.objects.count(), 2)

    def test_filter_chains_compose_with_scope(self):
        """User-level filters compose on top of the auto-applied tenant filter."""
        with override(agency_id=self.a.id):
            qs = User.tenant_objects.filter(email="a@test.com")
            self.assertEqual(qs.count(), 1)
            qs2 = User.tenant_objects.filter(email="b@test.com")
            # Email matches but agency doesn't — must return zero
            self.assertEqual(qs2.count(), 0)


# ─────────────────────────────────────────────────────────────────
# Middleware
# ─────────────────────────────────────────────────────────────────


class TenantContextMiddlewareTest(TestCase):
    def setUp(self):
        _reset_local()
        self.factory = RequestFactory()
        self.agency = _make_agency("MW Agency")
        self.user = _make_user("mw@test.com", agency=self.agency)

    def _middleware(self, response_value="ok"):
        seen: dict = {"agency_id": None, "bypass": None}

        def get_response(request):
            seen["agency_id"] = current_agency_id()
            seen["bypass"] = is_bypass_active()
            return response_value

        return TenantContextMiddleware(get_response), seen

    def test_authenticated_user_populates_context(self):
        mw, seen = self._middleware()
        request = self.factory.get("/")
        request.user = self.user
        mw(request)
        self.assertEqual(seen["agency_id"], self.agency.id)
        self.assertFalse(seen["bypass"])

    def test_anonymous_user_leaves_context_empty(self):
        mw, seen = self._middleware()
        request = self.factory.get("/")
        request.user = AnonymousUser()
        mw(request)
        self.assertIsNone(seen["agency_id"])

    def test_user_without_agency_leaves_context_empty(self):
        mw, seen = self._middleware()
        orphan = _make_user("orphan@test.com", agency=None)
        request = self.factory.get("/")
        request.user = orphan
        mw(request)
        self.assertIsNone(seen["agency_id"])

    def test_context_cleared_after_response(self):
        mw, _ = self._middleware()
        request = self.factory.get("/")
        request.user = self.user
        mw(request)
        # Context cleared between requests — reading from outside should be empty
        self.assertIsNone(current_agency_id())

    def test_context_cleared_even_on_exception(self):
        def raising_response(request):
            raise RuntimeError("view exploded")

        mw = TenantContextMiddleware(raising_response)
        request = self.factory.get("/")
        request.user = self.user
        with self.assertRaises(RuntimeError):
            mw(request)
        self.assertIsNone(current_agency_id())

    def test_two_sequential_requests_dont_leak(self):
        """Different users in successive requests must see their own agencies."""
        mw, seen = self._middleware()

        # First request — agency A user
        r1 = self.factory.get("/")
        r1.user = self.user
        mw(r1)
        first_seen = seen["agency_id"]

        # Second request — anonymous user, must not inherit from r1
        r2 = self.factory.get("/")
        r2.user = AnonymousUser()
        mw(r2)
        second_seen = seen["agency_id"]

        self.assertEqual(first_seen, self.agency.id)
        self.assertIsNone(second_seen)
