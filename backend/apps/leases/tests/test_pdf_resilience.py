"""
PDF render resilience tests — RNT-QUAL-002.

Covers:
  - Gotenberg client: 3 retries with exponential backoff on 5xx/timeout
  - Final failure enqueues PdfRenderJob (or uses thread-based equivalent)
  - Success path emits Sentry metrics
  - PdfRenderJob task: worker retries, marks DONE on success, FAILED when exhausted
  - ExportTemplatePDFView: returns 202 + job_id when Gotenberg is down

Run with:
    pytest backend/apps/leases/tests/test_pdf_resilience.py -v
"""
from __future__ import annotations

import pytest
import requests as req_lib
from unittest.mock import MagicMock, patch, call


pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Gotenberg client — retry behaviour
# ---------------------------------------------------------------------------

class TestGotenbergRetry:
    """html_to_pdf(): retries on 5xx and timeout, gives up after MAX_RETRIES."""

    @patch("time.sleep")  # eliminate real sleeps in tests
    @patch("apps.esigning.gotenberg.requests.post")
    def test_retries_three_times_on_5xx(self, mock_post, mock_sleep):
        from apps.esigning.gotenberg import html_to_pdf, MAX_RETRIES

        bad = MagicMock()
        bad.ok = False
        bad.status_code = 500
        bad.text = "Internal Server Error"

        good = MagicMock()
        good.ok = True
        good.content = b"%PDF-ok"

        # First two calls fail, third succeeds
        mock_post.side_effect = [bad, bad, good]

        result = html_to_pdf("<html></html>")
        assert result == b"%PDF-ok"
        assert mock_post.call_count == 3
        # Should have slept twice (after attempt 1 and 2)
        assert mock_sleep.call_count == 2

    @patch("time.sleep")
    @patch("apps.esigning.gotenberg.requests.post")
    def test_retries_on_timeout(self, mock_post, mock_sleep):
        from apps.esigning.gotenberg import html_to_pdf

        good = MagicMock()
        good.ok = True
        good.content = b"%PDF-ok"

        mock_post.side_effect = [req_lib.Timeout("timed out"), good]

        result = html_to_pdf("<html></html>")
        assert result == b"%PDF-ok"
        assert mock_post.call_count == 2
        assert mock_sleep.call_count == 1

    @patch("time.sleep")
    @patch("apps.esigning.gotenberg.requests.post")
    def test_raises_after_all_retries_exhausted(self, mock_post, mock_sleep):
        from apps.esigning.gotenberg import html_to_pdf, MAX_RETRIES

        bad = MagicMock()
        bad.ok = False
        bad.status_code = 503
        bad.text = "Service Unavailable"

        # All attempts fail
        mock_post.return_value = bad

        with pytest.raises(Exception):
            html_to_pdf("<html></html>")

        assert mock_post.call_count == MAX_RETRIES + 1
        assert mock_sleep.call_count == MAX_RETRIES  # no sleep after last attempt

    @patch("time.sleep")
    @patch("apps.esigning.gotenberg.requests.post")
    def test_backoff_doubles_each_attempt(self, mock_post, mock_sleep):
        from apps.esigning.gotenberg import html_to_pdf, RETRY_BACKOFF_BASE

        bad = MagicMock()
        bad.ok = False
        bad.status_code = 503
        bad.text = "down"
        mock_post.return_value = bad

        with pytest.raises(Exception):
            html_to_pdf("<html></html>")

        sleep_calls = [c.args[0] for c in mock_sleep.call_args_list]
        # Verify exponential growth: 1, 2, 4 …
        for i, delay in enumerate(sleep_calls):
            expected = RETRY_BACKOFF_BASE * (2 ** i)
            assert delay == expected, f"Expected sleep {expected}s at attempt {i+1}, got {delay}"

    @patch("time.sleep")
    @patch("apps.esigning.gotenberg.requests.post")
    def test_success_on_first_try_does_not_sleep(self, mock_post, mock_sleep):
        from apps.esigning.gotenberg import html_to_pdf

        good = MagicMock()
        good.ok = True
        good.content = b"%PDF"
        mock_post.return_value = good

        html_to_pdf("<html></html>")
        mock_sleep.assert_not_called()


# ---------------------------------------------------------------------------
# Gotenberg client — Sentry metrics
# ---------------------------------------------------------------------------

class TestGotenbergMetrics:
    """Success and failure paths emit Sentry metrics."""

    @patch("time.sleep")
    @patch("apps.esigning.gotenberg.requests.post")
    def test_emits_success_counter(self, mock_post, mock_sleep):
        from apps.esigning import gotenberg

        good = MagicMock()
        good.ok = True
        good.content = b"%PDF"
        mock_post.return_value = good

        captured_names: list[str] = []

        def capture(name, tags=None):
            captured_names.append(name)

        with patch.object(gotenberg, '_increment_counter', side_effect=capture):
            gotenberg.html_to_pdf("<html></html>")

        assert 'gotenberg.pdf.success' in captured_names, \
            f"Expected gotenberg.pdf.success counter call, got: {captured_names}"

    @patch("time.sleep")
    @patch("apps.esigning.gotenberg.requests.post")
    def test_emits_failure_counter_on_5xx(self, mock_post, mock_sleep):
        from apps.esigning import gotenberg

        bad = MagicMock()
        bad.ok = False
        bad.status_code = 500
        bad.text = "err"
        mock_post.return_value = bad

        failure_names = []

        original_incr = gotenberg._increment_counter

        def capture(name, tags=None):
            failure_names.append(name)

        with patch.object(gotenberg, '_increment_counter', side_effect=capture):
            with pytest.raises(Exception):
                gotenberg.html_to_pdf("<html></html>")

        assert 'gotenberg.pdf.failure' in failure_names

    @patch("time.sleep")
    @patch("apps.esigning.gotenberg.requests.post")
    def test_emits_latency_metric_on_success(self, mock_post, mock_sleep):
        from apps.esigning import gotenberg

        good = MagicMock()
        good.ok = True
        good.content = b"%PDF"
        mock_post.return_value = good

        metric_names = []

        def capture(name, value, unit="none", tags=None):
            metric_names.append(name)

        with patch.object(gotenberg, '_emit_metric', side_effect=capture):
            gotenberg.html_to_pdf("<html></html>")

        assert 'gotenberg.pdf.latency_ms' in metric_names


# ---------------------------------------------------------------------------
# PdfRenderJob task: background worker
# ---------------------------------------------------------------------------

class TestPdfRenderJobTask:
    """Background retry worker: marks DONE on success, FAILED on exhaustion."""

    @pytest.fixture()
    def make_job(self, db):
        """Create a real PdfRenderJob row (requires Django DB)."""
        from apps.leases.models import PdfRenderJob, LeaseTemplate
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user, _ = User.objects.get_or_create(email='test@test.com', defaults={'role': 'admin'})
        job = PdfRenderJob.objects.create(html_payload='<html></html>', requested_by=user)
        return job

    @patch("apps.leases.tasks._RETRY_DELAY_SECONDS", 0)  # no sleeping in tests
    @patch("time.sleep")
    @patch("apps.esigning.gotenberg.requests.post")
    @pytest.mark.django_db
    def test_worker_marks_done_on_success(self, mock_post, mock_sleep, make_job):
        from apps.leases.tasks import _attempt_render
        from apps.leases.models import PdfRenderJob

        good = MagicMock()
        good.ok = True
        good.content = b"%PDF-1.4 success"
        mock_post.return_value = good

        _attempt_render(make_job.id)

        make_job.refresh_from_db()
        assert make_job.status == PdfRenderJob.Status.DONE
        assert make_job.result_pdf

    @patch("apps.leases.tasks._RETRY_DELAY_SECONDS", 0)
    @patch("time.sleep")
    @patch("apps.esigning.gotenberg.requests.post")
    @pytest.mark.django_db
    def test_worker_marks_failed_after_max_attempts(self, mock_post, mock_sleep, make_job):
        from apps.leases.tasks import _attempt_render
        from apps.leases.models import PdfRenderJob

        bad = MagicMock()
        bad.ok = False
        bad.status_code = 503
        bad.text = "down"
        mock_post.return_value = bad

        _attempt_render(make_job.id)

        make_job.refresh_from_db()
        assert make_job.status == PdfRenderJob.Status.FAILED
        assert make_job.attempts == PdfRenderJob.MAX_ATTEMPTS

    @patch("apps.leases.tasks._RETRY_DELAY_SECONDS", 0)
    @patch("time.sleep")
    @patch("apps.esigning.gotenberg.requests.post")
    @pytest.mark.django_db
    def test_worker_succeeds_on_second_attempt(self, mock_post, mock_sleep, make_job):
        from apps.leases.tasks import _attempt_render
        from apps.leases.models import PdfRenderJob

        bad = MagicMock()
        bad.ok = False
        bad.status_code = 503
        bad.text = "down"

        good = MagicMock()
        good.ok = True
        good.content = b"%PDF-1.4 ok"

        # All the Gotenberg-internal retries (MAX_RETRIES+1 = 4) fail on first worker attempt,
        # then succeed on second worker attempt.
        mock_post.side_effect = [bad] * 4 + [good]

        _attempt_render(make_job.id)

        make_job.refresh_from_db()
        assert make_job.status == PdfRenderJob.Status.DONE


# ---------------------------------------------------------------------------
# ExportTemplatePDFView — graceful fallback
# ---------------------------------------------------------------------------

class TestExportTemplatePDFViewFallback:
    """ExportTemplatePDFView returns 202 + job_id when Gotenberg fails."""

    @pytest.mark.django_db
    @patch("apps.leases.tasks.enqueue_pdf_render")
    @patch("apps.esigning.gotenberg.requests.post")
    def test_returns_202_when_gotenberg_fails(self, mock_post, mock_enqueue, client, db):
        from django.contrib.auth import get_user_model
        from apps.accounts.models import Agency
        from apps.leases.models import LeaseTemplate
        from rest_framework.test import APIClient

        User = get_user_model()
        agency = Agency.objects.create(name="PDF Resilience Agency")
        user, _ = User.objects.get_or_create(
            email='agent@test.com',
            defaults={'role': 'agent'},
        )
        user.set_password('pass')
        user.agency = agency
        user.save()

        template = LeaseTemplate.objects.create(
            agency=agency,
            name='Test Template',
            content_html='<p>Hello {{name}}</p>',
        )

        # Make Gotenberg fail on all retries
        bad = MagicMock()
        bad.ok = False
        bad.status_code = 503
        bad.text = "down"
        mock_post.return_value = bad

        api = APIClient()
        api.force_authenticate(user=user)

        with patch("time.sleep"):
            resp = api.get(f'/api/v1/leases/templates/{template.id}/export.pdf/')

        assert resp.status_code == 202
        data = resp.json()
        assert data['queued'] is True
        assert 'job_id' in data
        assert 'email you when ready' in data['message']

    @pytest.mark.django_db
    @patch("apps.esigning.gotenberg.requests.post")
    def test_returns_pdf_bytes_when_gotenberg_succeeds(self, mock_post, db):
        from django.contrib.auth import get_user_model
        from apps.accounts.models import Agency
        from apps.leases.models import LeaseTemplate
        from rest_framework.test import APIClient

        User = get_user_model()
        agency = Agency.objects.create(name="PDF Resilience Agency 2")
        user, _ = User.objects.get_or_create(
            email='agent2@test.com',
            defaults={'role': 'agent'},
        )
        user.agency = agency
        user.save()

        template = LeaseTemplate.objects.create(
            agency=agency,
            name='Test Template 2',
            content_html='<p>Hello</p>',
        )

        good = MagicMock()
        good.ok = True
        good.content = b"%PDF-1.4 real-content"
        mock_post.return_value = good

        api = APIClient()
        api.force_authenticate(user=user)

        resp = api.get(f'/api/v1/leases/templates/{template.id}/export.pdf/')

        assert resp.status_code == 200
        assert resp['Content-Type'] == 'application/pdf'
