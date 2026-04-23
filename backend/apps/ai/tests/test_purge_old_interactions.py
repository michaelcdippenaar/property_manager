"""
Tests for the purge_old_interactions management command.

Covers:
  - Stale GuideInteraction rows are deleted
  - Fresh GuideInteraction rows are retained
  - Stale TenantChatSession rows are deleted (by updated_at)
  - Fresh TenantChatSession rows are retained
  - --dry-run reports counts but deletes nothing
  - --days=N override is honoured

Run with:
    cd backend && pytest apps/ai/tests/test_purge_old_interactions.py -v
"""
from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone

from apps.ai.models import GuideInteraction, TenantChatSession

User = get_user_model()

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="purge_test@test.klikk.co.za",
        password="testpass123",
        role="AGENT",
    )


def _make_guide_interaction(user, *, days_ago: int) -> GuideInteraction:
    """Create a GuideInteraction and backdate its created_at."""
    gi = GuideInteraction.objects.create(
        user=user,
        portal=GuideInteraction.PORTAL_AGENT,
        message="test message",
    )
    # auto_now_add sets created_at; bypass it with queryset update
    GuideInteraction.objects.filter(pk=gi.pk).update(
        created_at=timezone.now() - timedelta(days=days_ago)
    )
    gi.refresh_from_db()
    return gi


def _make_tenant_session(user, *, days_ago: int) -> TenantChatSession:
    """Create a TenantChatSession and backdate its updated_at."""
    session = TenantChatSession.objects.create(user=user)
    # auto_now sets updated_at on every save; bypass with queryset update
    TenantChatSession.objects.filter(pk=session.pk).update(
        updated_at=timezone.now() - timedelta(days=days_ago)
    )
    session.refresh_from_db()
    return session


# ---------------------------------------------------------------------------
# GuideInteraction tests
# ---------------------------------------------------------------------------


class TestPurgeGuideInteractions:
    def test_stale_guide_interaction_is_deleted(self, user):
        stale = _make_guide_interaction(user, days_ago=91)
        call_command("purge_old_interactions")
        assert not GuideInteraction.objects.filter(pk=stale.pk).exists()

    def test_fresh_guide_interaction_is_retained(self, user):
        fresh = _make_guide_interaction(user, days_ago=10)
        call_command("purge_old_interactions")
        assert GuideInteraction.objects.filter(pk=fresh.pk).exists()

    def test_only_stale_deleted_leaves_fresh_intact(self, user):
        stale = _make_guide_interaction(user, days_ago=100)
        fresh = _make_guide_interaction(user, days_ago=30)
        call_command("purge_old_interactions")
        assert not GuideInteraction.objects.filter(pk=stale.pk).exists()
        assert GuideInteraction.objects.filter(pk=fresh.pk).exists()

    def test_boundary_exactly_at_cutoff_is_deleted(self, user):
        # A record created exactly at the cutoff (91 days ago) is stale.
        boundary = _make_guide_interaction(user, days_ago=91)
        call_command("purge_old_interactions")
        assert not GuideInteraction.objects.filter(pk=boundary.pk).exists()

    def test_record_one_day_inside_window_is_retained(self, user):
        inside = _make_guide_interaction(user, days_ago=89)
        call_command("purge_old_interactions")
        assert GuideInteraction.objects.filter(pk=inside.pk).exists()


# ---------------------------------------------------------------------------
# TenantChatSession tests
# ---------------------------------------------------------------------------


class TestPurgeTenantChatSessions:
    def test_stale_session_is_deleted(self, user):
        stale = _make_tenant_session(user, days_ago=91)
        call_command("purge_old_interactions")
        assert not TenantChatSession.objects.filter(pk=stale.pk).exists()

    def test_fresh_session_is_retained(self, user):
        fresh = _make_tenant_session(user, days_ago=5)
        call_command("purge_old_interactions")
        assert TenantChatSession.objects.filter(pk=fresh.pk).exists()

    def test_only_stale_sessions_deleted(self, user):
        stale = _make_tenant_session(user, days_ago=95)
        fresh = _make_tenant_session(user, days_ago=45)
        call_command("purge_old_interactions")
        assert not TenantChatSession.objects.filter(pk=stale.pk).exists()
        assert TenantChatSession.objects.filter(pk=fresh.pk).exists()


# ---------------------------------------------------------------------------
# --dry-run
# ---------------------------------------------------------------------------


class TestDryRun:
    def test_dry_run_deletes_nothing_guide_interaction(self, user):
        stale = _make_guide_interaction(user, days_ago=100)
        call_command("purge_old_interactions", dry_run=True)
        assert GuideInteraction.objects.filter(pk=stale.pk).exists()

    def test_dry_run_deletes_nothing_tenant_session(self, user):
        stale = _make_tenant_session(user, days_ago=100)
        call_command("purge_old_interactions", dry_run=True)
        assert TenantChatSession.objects.filter(pk=stale.pk).exists()

    def test_dry_run_does_not_affect_fresh_rows(self, user):
        fresh_gi = _make_guide_interaction(user, days_ago=5)
        fresh_ts = _make_tenant_session(user, days_ago=5)
        call_command("purge_old_interactions", dry_run=True)
        assert GuideInteraction.objects.filter(pk=fresh_gi.pk).exists()
        assert TenantChatSession.objects.filter(pk=fresh_ts.pk).exists()


# ---------------------------------------------------------------------------
# --days=N override
# ---------------------------------------------------------------------------


class TestDaysOverride:
    def test_custom_days_deletes_within_narrower_window(self, user):
        """--days=30 should delete a 35-day-old record that default 90 would keep."""
        record = _make_guide_interaction(user, days_ago=35)
        call_command("purge_old_interactions", days=30)
        assert not GuideInteraction.objects.filter(pk=record.pk).exists()

    def test_custom_days_retains_outside_narrower_window(self, user):
        """--days=30: a 20-day-old record should be retained."""
        record = _make_guide_interaction(user, days_ago=20)
        call_command("purge_old_interactions", days=30)
        assert GuideInteraction.objects.filter(pk=record.pk).exists()

    def test_custom_days_wider_window_retains_record(self, user):
        """--days=180: a 91-day-old record (stale under default) should be retained."""
        record = _make_guide_interaction(user, days_ago=91)
        call_command("purge_old_interactions", days=180)
        assert GuideInteraction.objects.filter(pk=record.pk).exists()

    def test_custom_days_session_narrower_window(self, user):
        """--days=30 deletes a 35-day-old session."""
        session = _make_tenant_session(user, days_ago=35)
        call_command("purge_old_interactions", days=30)
        assert not TenantChatSession.objects.filter(pk=session.pk).exists()

    def test_custom_days_dry_run_combined(self, user):
        """--dry-run combined with --days=30 still deletes nothing."""
        record = _make_guide_interaction(user, days_ago=35)
        call_command("purge_old_interactions", days=30, dry_run=True)
        assert GuideInteraction.objects.filter(pk=record.pk).exists()
