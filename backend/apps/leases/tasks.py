"""
Background tasks for the leases app.

# Async/Celery tasks: use apps.accounts.tenancy.tenant_context_for_task(agency_id=...)
# (or apps.accounts.tenancy.override(...)) before any tenant_objects access.
# See QA round 5 bug 3. Current bodies use `Model.objects` (unscoped) and so
# work today; refactors to `tenant_objects` MUST set tenant context first or
# the queryset will silently return .none().

No Celery in this project — we use fire-and-forget threads (same pattern as
apps/properties/tasks.py).  If Celery is added later, replace
``_run_in_thread`` with ``@shared_task.apply_async``.

Public entry points
-------------------
enqueue_pdf_render(job_id)
    Schedule a PdfRenderJob for background retry.  Safe to call from a view
    immediately after the job row is committed to the DB.
"""
from __future__ import annotations

import io
import logging
import threading
import time

from django.core.files.base import ContentFile
from django.db import transaction

logger = logging.getLogger(__name__)

# Delay between retry attempts inside the background worker.
# This is separate from the per-request backoff inside gotenberg.html_to_pdf
# — the worker-level delay gives Gotenberg time to recover between jobs.
_RETRY_DELAY_SECONDS = 300   # 5 minutes between worker-level attempts


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _run_in_thread(fn, *args, **kwargs) -> None:
    """Fire-and-forget worker thread."""
    name = f"pdf_render_{args[0] if args else 'job'}"
    t = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True, name=name)
    t.start()


def _attempt_render(job_id: int) -> None:
    """
    Worker body: fetch the job, call Gotenberg (with its own internal retries),
    save the PDF if successful, or mark FAILED when MAX_ATTEMPTS is exhausted.

    Each call to this function counts as one attempt.  Between failed attempts
    the thread sleeps for _RETRY_DELAY_SECONDS before trying again.
    """
    from apps.leases.models import PdfRenderJob
    from apps.esigning.gotenberg import html_to_pdf

    try:
        job = PdfRenderJob.objects.get(pk=job_id)
    except PdfRenderJob.DoesNotExist:
        logger.warning("PdfRenderJob %s not found — aborting worker", job_id)
        return

    while job.attempts < PdfRenderJob.MAX_ATTEMPTS:
        job.status = PdfRenderJob.Status.RUNNING
        job.attempts += 1
        job.save(update_fields=["status", "attempts", "updated_at"])

        try:
            pdf_bytes = html_to_pdf(job.html_payload)
        except Exception as exc:
            logger.warning(
                "PdfRenderJob %s attempt %d/%d failed: %s",
                job_id, job.attempts, PdfRenderJob.MAX_ATTEMPTS, exc,
            )
            job.error = str(exc)
            if job.attempts >= PdfRenderJob.MAX_ATTEMPTS:
                job.status = PdfRenderJob.Status.FAILED
                job.save(update_fields=["status", "error", "updated_at"])
                logger.error(
                    "PdfRenderJob %s exhausted all %d attempts — marked FAILED",
                    job_id, PdfRenderJob.MAX_ATTEMPTS,
                )
                return
            else:
                job.status = PdfRenderJob.Status.PENDING
                job.save(update_fields=["status", "error", "updated_at"])
                logger.info(
                    "PdfRenderJob %s sleeping %ds before next attempt",
                    job_id, _RETRY_DELAY_SECONDS,
                )
                time.sleep(_RETRY_DELAY_SECONDS)
                # Re-read job in case it was cancelled externally
                try:
                    job = PdfRenderJob.objects.get(pk=job_id)
                except PdfRenderJob.DoesNotExist:
                    return
        else:
            # Success — persist the rendered PDF
            template_name = (job.template.name if job.template else "render") or "render"
            safe = "".join(c for c in template_name if c.isalnum() or c in "-_ ")[:40]
            filename = f"{safe.strip().replace(' ', '_') or 'render'}_{job_id}.pdf"
            job.result_pdf.save(filename, ContentFile(pdf_bytes), save=False)
            job.status = PdfRenderJob.Status.DONE
            job.error = ""
            job.save(update_fields=["result_pdf", "status", "error", "updated_at"])
            logger.info("PdfRenderJob %s completed successfully", job_id)
            return


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def enqueue_pdf_render(job_id: int) -> None:
    """
    Schedule a PdfRenderJob for background retry.

    Uses ``transaction.on_commit`` so the job row is visible to the worker
    thread before it starts.
    """
    transaction.on_commit(lambda: _run_in_thread(_attempt_render, job_id))
