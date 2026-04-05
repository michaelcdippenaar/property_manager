"""
test_hub models — health tracking, issue lifecycle, and self-testing.

These models power:
- The Vue developer portal (test dashboard, coverage stats, issue tracker)
- Feedback loops (AI learns from test outcomes to improve future tests)
- Meta self-testing (the test_hub tests itself)
- RAG store freshness tracking
"""
from django.db import models
from django.utils import timezone


MODULES = [
    "accounts", "properties", "leases", "maintenance",
    "esigning", "ai", "tenant_portal", "notifications",
]

MODULE_CHOICES = [(m, m.replace("_", " ").title()) for m in MODULES]

TIER_CHOICES = [
    ("unit", "Unit"),
    ("integration", "Integration"),
    ("e2e", "E2E"),
    ("all", "All"),
]

PHASE_CHOICES = [
    ("red", "Red (pending)"),
    ("green", "Green (passing)"),
    ("all", "All"),
]

TRIGGER_CHOICES = [
    ("manual", "Manual"),
    ("ai_agent", "AI Agent"),
    ("ci", "CI/CD"),
    ("scheduled", "Scheduled"),
]


class TestRunRecord(models.Model):
    """
    Historical record of every test run.
    Written by `run_tdd` management command and CI hooks.
    Powers the trend graphs in the developer portal.
    """
    module = models.CharField(max_length=50, choices=MODULE_CHOICES + [("all", "All")], db_index=True)
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default="all")
    phase = models.CharField(max_length=20, choices=PHASE_CHOICES, default="all")
    run_at = models.DateTimeField(auto_now_add=True, db_index=True)
    triggered_by = models.CharField(max_length=20, choices=TRIGGER_CHOICES, default="manual")

    tests_run = models.IntegerField(default=0)
    tests_passed = models.IntegerField(default=0)
    tests_failed = models.IntegerField(default=0)
    tests_xfailed = models.IntegerField(default=0)   # red tests (expected failures)
    tests_xpassed = models.IntegerField(default=0)   # red tests that unexpectedly passed (bad!)
    tests_skipped = models.IntegerField(default=0)

    duration_seconds = models.FloatField(default=0)
    coverage_percent = models.FloatField(null=True, blank=True)
    raw_output = models.TextField(blank=True)

    class Meta:
        ordering = ["-run_at"]
        verbose_name = "Test Run Record"

    def __str__(self):
        return f"{self.module} [{self.tier}] @ {self.run_at:%Y-%m-%d %H:%M} — {self.tests_passed}/{self.tests_run} passed"

    @property
    def pass_rate(self) -> float:
        if not self.tests_run:
            return 0.0
        return round(self.tests_passed / self.tests_run * 100, 1)

    @property
    def has_regressions(self) -> bool:
        """True if any green test failed or any red test unexpectedly passed."""
        return self.tests_failed > 0 or self.tests_xpassed > 0


class TestIssue(models.Model):
    """
    A bug found during manual testing.
    Lifecycle: RED (discovered) → FIXED (test passes, user confirmed).
    Synced from the issues/<module>/<date>_<slug>.md files.
    """
    STATUS_RED = "red"
    STATUS_FIXED = "fixed"
    STATUS_CHOICES = [(STATUS_RED, "RED — fix pending"), (STATUS_FIXED, "FIXED — test green")]

    module = models.CharField(max_length=50, choices=MODULE_CHOICES, db_index=True)
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_RED, db_index=True)

    discovered_at = models.DateField(db_index=True)
    fixed_at = models.DateField(null=True, blank=True)

    test_file = models.CharField(max_length=500, blank=True, help_text="Path to the red/green test")
    issue_file_path = models.CharField(max_length=500, help_text="Path to the .md issue file")
    description = models.TextField(blank=True)
    root_cause = models.TextField(blank=True)

    class Meta:
        ordering = ["-discovered_at"]
        unique_together = [("module", "slug")]
        verbose_name = "Test Issue"

    def __str__(self):
        return f"[{self.status.upper()}] {self.module}: {self.title}"

    @property
    def days_open(self) -> int | None:
        if self.status == self.STATUS_FIXED:
            return None
        return (timezone.now().date() - self.discovered_at).days


class TestHealthSnapshot(models.Model):
    """
    Periodic health snapshot of the full test suite.
    Created by `run_tdd --snapshot` — used for trend analysis and portal dashboard.
    """
    taken_at = models.DateTimeField(auto_now_add=True, db_index=True)

    total_tests = models.IntegerField(default=0)
    total_green = models.IntegerField(default=0)
    total_red = models.IntegerField(default=0)        # pending implementations
    total_unit = models.IntegerField(default=0)
    total_integration = models.IntegerField(default=0)
    total_e2e = models.IntegerField(default=0)

    open_issues = models.IntegerField(default=0)
    fixed_issues = models.IntegerField(default=0)
    avg_days_to_fix = models.FloatField(null=True, blank=True)

    coverage_percent = models.FloatField(null=True, blank=True)
    rag_last_indexed = models.DateTimeField(null=True, blank=True)

    # Per-module breakdown stored as JSON
    module_breakdown = models.JSONField(default=dict, help_text="Per-module test counts")

    class Meta:
        ordering = ["-taken_at"]
        verbose_name = "Test Health Snapshot"

    def __str__(self):
        return f"Health @ {self.taken_at:%Y-%m-%d %H:%M} — {self.total_green} green / {self.total_red} red"

    @property
    def health_score(self) -> float:
        """
        0–100 score. 100 = all tests green, zero open issues, high coverage.
        Penalises: open issues, red tests with no activity, low coverage.
        """
        if not self.total_tests:
            return 0.0
        base = (self.total_green / self.total_tests) * 70
        coverage_score = (self.coverage_percent or 0) / 100 * 20
        issue_penalty = min(self.open_issues * 2, 10)
        return round(base + coverage_score - issue_penalty, 1)


class TestModuleSelfHealth(models.Model):
    """
    Meta-model: the test_hub tests ITSELF.

    Tracks integrity of the test_hub app:
    - Are all context files present and non-empty?
    - Is the RAG store populated and fresh?
    - Are all modules represented in both unit/ and integration/?
    - Are all issue .md files synced to TestIssue records?
    - Does conftest.py enforce xfail on red tests?
    - Are there any orphaned test files (no __init__.py)?
    - Are there duplicate test names across the suite?

    Created by `python manage.py test_hub_selfcheck`.
    """
    checked_at = models.DateTimeField(auto_now_add=True)
    is_healthy = models.BooleanField(default=False)

    context_files_ok = models.BooleanField(default=False, help_text="All 8 module context files exist and are non-empty")
    rag_store_ok = models.BooleanField(default=False, help_text="test_context ChromaDB collection has documents")
    rag_last_indexed = models.DateTimeField(null=True, blank=True)
    all_modules_have_tests = models.BooleanField(default=False, help_text="Every module has at least one unit/ and integration/ test")
    issues_synced = models.BooleanField(default=False, help_text="All issue .md files have matching TestIssue DB records")
    no_duplicate_test_names = models.BooleanField(default=False, help_text="No duplicate test method names across the suite")
    no_orphaned_files = models.BooleanField(default=False, help_text="All test directories have __init__.py")
    conftest_enforces_xfail = models.BooleanField(default=False, help_text="conftest.py enforces xfail strict on @pytest.mark.red")

    issues_found = models.JSONField(default=list, help_text="List of integrity issues found during self-check")
    warnings = models.JSONField(default=list, help_text="Non-critical warnings")

    class Meta:
        ordering = ["-checked_at"]
        verbose_name = "Test Module Self-Health"

    def __str__(self):
        status = "HEALTHY" if self.is_healthy else "ISSUES FOUND"
        return f"Self-check @ {self.checked_at:%Y-%m-%d %H:%M} — {status}"
