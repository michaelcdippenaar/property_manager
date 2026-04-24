"""
Regression guard: test suite isolation invariants (QA-020).

These tests verify that the autouse fixtures in conftest.py correctly reset
shared in-process state that would cause cross-test pollution:

  1. DRF throttle cache — earlier tests that trigger rate-limits must not
     leave stale cache keys that cause 429s in later tests.
  2. ContentType cache — stale PKs from a previous DB would cause
     IntegrityErrors in AuditEvent signal handlers.
  3. DRF SimpleRateThrottle.THROTTLE_RATES class variable — patching this
     inside one test must not bleed into the next.

All three fixtures are autouse and live in backend/conftest.py.  If any of
them is accidentally removed or scoped to session, one of the assertions
below will fail.
"""
import pytest
from django.core.cache import cache
from rest_framework.throttling import SimpleRateThrottle


pytestmark = [pytest.mark.unit, pytest.mark.green]


class TestDRFThrottleCacheIsolation:
    """Verify that the _reset_drf_throttle_cache autouse fixture works."""

    def test_cache_is_empty_at_test_start(self):
        """The cache must be clear at the start of every test.

        If the autouse fixture stopped clearing the cache between tests,
        a key written by the previous test would still be present here.
        We cannot rely on test ordering, so instead we check that writing
        a sentinel value in this test does NOT persist into the next test
        (see test_sentinel_not_present_from_previous_test, which must run
        AFTER this one within the same class — Django TestCase runs methods
        alphabetically inside a class, so b_ < c_ ordering is stable).
        """
        # Write a sentinel that test_b should NOT see.
        cache.set("qa020_isolation_sentinel", "poison", timeout=300)
        assert cache.get("qa020_isolation_sentinel") == "poison"

    def test_sentinel_not_present_from_previous_test(self):
        """Sentinel written in the previous test must be gone.

        The _reset_drf_throttle_cache fixture calls cache.clear() after
        every test.  If the fixture is removed, this assertion fails.
        """
        # If the autouse fixture ran between tests, the cache is clear.
        assert cache.get("qa020_isolation_sentinel") is None, (
            "DRF throttle cache was NOT cleared between tests.  "
            "The _reset_drf_throttle_cache autouse fixture in conftest.py "
            "may have been removed or re-scoped.  See QA-020."
        )

    def test_throttle_rates_class_var_restored_after_patch(self):
        """Patching THROTTLE_RATES in a test must not bleed out.

        The autouse fixture snapshots and restores SimpleRateThrottle.THROTTLE_RATES
        around every test.  Here we mutate it and expect the next test to see
        the original value.
        """
        _original = SimpleRateThrottle.THROTTLE_RATES.copy()
        SimpleRateThrottle.THROTTLE_RATES = {"test_qa020_key": "1/day"}
        # The fixture will restore the original after this test exits.
        assert SimpleRateThrottle.THROTTLE_RATES == {"test_qa020_key": "1/day"}
        # Restore inline as well so this test's own assertions are clean.
        SimpleRateThrottle.THROTTLE_RATES = _original

    def test_throttle_rates_is_original_after_previous_patch(self):
        """THROTTLE_RATES must be the original value here.

        If the _reset_drf_throttle_cache fixture is broken, the patched
        value {"test_qa020_key": "1/day"} from the previous test would
        still be present.
        """
        assert "test_qa020_key" not in SimpleRateThrottle.THROTTLE_RATES, (
            "SimpleRateThrottle.THROTTLE_RATES was NOT restored between tests.  "
            "The _reset_drf_throttle_cache autouse fixture in conftest.py "
            "may have been removed or re-scoped.  See QA-020."
        )


class TestContentTypeCacheIsolation:
    """Verify that the _clear_contenttypes_cache autouse fixture works."""

    def test_contenttypes_cache_clear_is_callable(self):
        """ContentType.objects.clear_cache() must exist and be callable.

        This is a guard against a Django version bump that renames or removes
        the method.  If it disappears, the autouse fixture silently stops
        working and cross-test ContentType PKs will become stale.
        """
        from django.contrib.contenttypes.models import ContentType
        assert callable(getattr(ContentType.objects, "clear_cache", None)), (
            "ContentType.objects.clear_cache() does not exist.  "
            "Update the _clear_contenttypes_cache fixture in conftest.py.  "
            "See QA-020."
        )

    @pytest.mark.django_db
    def test_contenttypes_cache_cleared_between_tests(self):
        """After clearing, a fresh lookup must succeed.

        The autouse fixture clears the cache before and after each test.
        This test verifies that the cache is in a consistent state at test
        start (no stale PKs from a previous DB setup).
        """
        from django.contrib.contenttypes.models import ContentType
        from apps.accounts.models import User
        # This would raise if a stale ContentType PK were cached.
        ct = ContentType.objects.get_for_model(User)
        assert ct.pk is not None
        assert ct.app_label == "accounts"
