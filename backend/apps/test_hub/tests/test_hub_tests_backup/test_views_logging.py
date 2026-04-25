"""
Unit tests for test_hub views logging.

Verifies that previously-silent except blocks now emit log records so
E2E failures are discoverable in dev logs.

These are fast unit tests — no full HTTP stack, no auth setup.
"""
import logging
import sys
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_subprocess_result(stdout: str) -> MagicMock:
    result = MagicMock()
    result.stdout = stdout
    result.stderr = ""
    return result


# ---------------------------------------------------------------------------
# trigger_run: pytest output parse errors should be logged
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestParseCountLogging:
    """trigger_run view: malformed pytest output lines log warnings."""

    def _invoke(self, output_line: str, caplog):
        from apps.test_hub.views import TestRunRecordViewSet
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        request = factory.post("/fake/", {}, format="json")
        request.user = MagicMock(spec=["__bool__"])
        request.user.__bool__ = lambda self: True

        fake_result = _make_fake_subprocess_result(output_line + "\n")

        with patch("subprocess.run", return_value=fake_result), \
             patch("apps.test_hub.views.TestRunRecord") as mock_model:
            mock_model.objects.create.return_value = MagicMock(
                module="all", tier="all", phase="all", triggered_by="manual",
                tests_run=0, tests_passed=0, tests_failed=0, tests_xfailed=0,
                raw_output="",
            )
            viewset = TestRunRecordViewSet()
            viewset.format_kwarg = None
            viewset.request = request
            viewset.kwargs = {}
            with caplog.at_level(logging.WARNING, logger="apps.test_hub.views"):
                viewset.trigger_run(request)

        return caplog.records

    def test_passed_parse_failure_logs_warning(self, caplog):
        # First token is not an int -> ValueError -> should log
        records = self._invoke("  X passed,", caplog)
        assert any("passed" in r.message for r in records), records

    def test_failed_parse_failure_logs_warning(self, caplog):
        records = self._invoke("  1 passed, Y failed", caplog)
        assert any("failed" in r.message for r in records), records

    def test_xfailed_parse_failure_logs_warning(self, caplog):
        records = self._invoke("  1 passed, Z xfailed", caplog)
        assert any("xfailed" in r.message for r in records), records

    def test_valid_output_no_warning(self, caplog):
        # Properly formatted line should not produce any warnings
        records = self._invoke("  3 passed, 1 failed, 2 xfailed", caplog)
        assert not any(r.levelno >= logging.WARNING for r in records), records


# ---------------------------------------------------------------------------
# HealthDashboardView: unavailable RAG collection logs a warning
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRagCountLogging:
    """HealthDashboardView: missing RAG collection logs a WARNING, returns 200."""

    def test_rag_import_error_logs_warning(self, caplog):
        from apps.test_hub.views import HealthDashboardView
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        request = factory.get("/fake/")
        request.user = MagicMock()

        with patch("apps.test_hub.models.TestHealthSnapshot") as mock_snap, \
             patch("apps.test_hub.models.TestRunRecord") as mock_run, \
             patch("apps.test_hub.models.TestIssue") as mock_issue, \
             patch("apps.test_hub.models.TestModuleSelfHealth") as mock_self, \
             patch.dict("sys.modules", {"core": None, "core.contract_rag": None}):

            mock_snap.objects.first.return_value = None
            mock_run.objects.first.return_value = None
            mock_run.objects.filter.return_value.order_by.return_value.__getitem__ = lambda s, k: MagicMock(first=lambda: None)
            mock_issue.objects.filter.return_value.count.return_value = 0
            mock_self.objects.first.return_value = None

            view = HealthDashboardView()
            with caplog.at_level(logging.WARNING, logger="apps.test_hub.views"):
                response = view.get(request)

        assert response.status_code == 200
        assert any("RAG" in r.message for r in caplog.records), caplog.records
