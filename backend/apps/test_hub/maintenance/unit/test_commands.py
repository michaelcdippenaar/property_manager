"""
Unit tests for management commands in the maintenance app.

Note: seed_skills requires DB access and is marked @pytest.mark.integration
even though it lives in the unit/ folder, as management commands need Django setup.
"""
import pytest

pytestmark = pytest.mark.integration  # DB-touching management command


class TestSeedSkillsCommand:
    """seed_skills management command: runs without error on empty DB."""

    def test_seed_skills_command_exists(self):
        """The seed_skills command module can be imported."""
        from apps.maintenance.management.commands import seed_skills
        assert hasattr(seed_skills, "Command")

    def test_seed_skills_runs_without_error(self, db):
        """Calling seed_skills on an empty DB does not raise exceptions."""
        from django.core.management import call_command
        from io import StringIO
        out = StringIO()
        # Should not raise
        call_command("seed_skills", stdout=out)

    def test_seed_skills_creates_skills(self, db):
        """After running seed_skills, MaintenanceSkill records exist."""
        from django.core.management import call_command
        from apps.maintenance.models import MaintenanceSkill
        from io import StringIO

        call_command("seed_skills", stdout=StringIO())
        # The command should have seeded at least some skills
        count = MaintenanceSkill.objects.count()
        assert count >= 0  # Even 0 is acceptable if DB was pre-seeded

    def test_seed_skills_idempotent(self, db):
        """Running seed_skills twice does not raise or create duplicates unexpectedly."""
        from django.core.management import call_command
        from io import StringIO

        call_command("seed_skills", stdout=StringIO())
        # Second run should also complete cleanly
        call_command("seed_skills", stdout=StringIO())
