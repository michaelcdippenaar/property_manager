"""
Management command that polls DocuSeal API for submission status changes.

Replaces the need for DocuSeal webhooks to reach localhost during development.
Fetches status for all pending/in-progress submissions and processes updates
through the same logic as the webhook handler.

Usage:
    # One-shot poll
    python manage.py poll_docuseal

    # Continuous polling every 10 seconds
    python manage.py poll_docuseal --watch

    # Custom interval (seconds)
    python manage.py poll_docuseal --watch --interval 5
"""
import json
import logging
import time

from django.core.management.base import BaseCommand

from apps.esigning.models import ESigningSubmission
from apps.esigning.services import _docuseal_get
from apps.esigning.webhooks import (
    _activate_lease,
    _broadcast_ws,
    _email_signed_copy_to_signers,
    _notify_staff,
    _sync_signer_statuses,
    _update_single_signer,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Poll DocuSeal API for submission status changes (replaces webhooks for local dev)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--watch",
            action="store_true",
            help="Continuously poll at an interval",
        )
        parser.add_argument(
            "--interval",
            type=int,
            default=10,
            help="Polling interval in seconds (default: 10)",
        )

    def handle(self, *args, **options):
        watch = options["watch"]
        interval = options["interval"]

        if watch:
            self.stdout.write(
                self.style.SUCCESS(f"Polling DocuSeal every {interval}s — Ctrl+C to stop")
            )
            try:
                while True:
                    self._poll_all()
                    time.sleep(interval)
            except KeyboardInterrupt:
                self.stdout.write("\nStopped.")
        else:
            self._poll_all()

    def _poll_all(self):
        active_submissions = ESigningSubmission.objects.filter(
            status__in=[
                ESigningSubmission.Status.PENDING,
                ESigningSubmission.Status.IN_PROGRESS,
            ],
            docuseal_submission_id__gt="",
        ).select_related("lease__unit__property", "created_by")

        if not active_submissions.exists():
            self.stdout.write("  No active submissions to poll.")
            return

        for sub in active_submissions:
            try:
                self._poll_submission(sub)
            except Exception:
                logger.exception("Error polling submission pk=%s", sub.pk)
                self.stderr.write(
                    self.style.ERROR(f"  Error polling submission {sub.pk}")
                )

    def _poll_submission(self, sub: ESigningSubmission):
        ds_id = sub.docuseal_submission_id
        try:
            remote = _docuseal_get(f"/submissions/{ds_id}")
        except Exception as e:
            self.stderr.write(f"  API error for submission {ds_id}: {e}")
            return

        remote_status = (remote.get("status") or "").lower()
        submitters = remote.get("submitters") or []
        documents = remote.get("documents") or []

        # Map DocuSeal status → local status
        status_map = {
            "completed": ESigningSubmission.Status.COMPLETED,
            "pending": ESigningSubmission.Status.PENDING,
            "awaiting": ESigningSubmission.Status.PENDING,
            "declined": ESigningSubmission.Status.DECLINED,
            "expired": ESigningSubmission.Status.EXPIRED,
        }

        changed = False

        # Check individual submitter status changes
        for submitter in submitters:
            submitter_id = str(submitter.get("id", ""))
            submitter_status = (submitter.get("status") or "").lower()
            local_signer = sub.get_signer_by_submitter_id(submitter_id)

            if not local_signer:
                continue

            local_status = (local_signer.get("status") or "").lower()

            if submitter_status in ("completed", "signed") and local_status not in (
                "completed",
                "signed",
            ):
                # Signer completed — simulate form.completed
                self.stdout.write(
                    self.style.WARNING(
                        f"  Signer {submitter.get('name') or submitter.get('email')} "
                        f"completed on submission {ds_id}"
                    )
                )
                sub.signers = _update_single_signer(
                    sub.signers,
                    submitter_id,
                    {
                        "status": "completed",
                        "completed_at": submitter.get("completed_at"),
                    },
                )
                if sub.status == ESigningSubmission.Status.PENDING:
                    sub.status = ESigningSubmission.Status.IN_PROGRESS

                _broadcast_ws(
                    sub.pk,
                    {
                        "type": "signer_completed",
                        "submission_id": sub.pk,
                        "completed_signer": {
                            "id": submitter.get("id"),
                            "name": submitter.get("name", ""),
                            "email": submitter.get("email", ""),
                            "role": submitter.get("role", ""),
                            "status": "completed",
                        },
                        "signers": sub.signers,
                    },
                )

                _notify_staff(
                    sub,
                    "form.completed",
                    {"submitter": submitter},
                )
                changed = True

            elif submitter_status in ("opened",) and local_status not in (
                "opened",
                "completed",
                "signed",
            ):
                sub.signers = _update_single_signer(
                    sub.signers,
                    submitter_id,
                    {"status": "opened"},
                )
                if sub.status == ESigningSubmission.Status.PENDING:
                    sub.status = ESigningSubmission.Status.IN_PROGRESS
                _broadcast_ws(
                    sub.pk,
                    {
                        "type": "signer_viewed",
                        "submission_id": sub.pk,
                        "signer": {
                            "id": submitter.get("id"),
                            "name": submitter.get("name", ""),
                            "email": submitter.get("email", ""),
                            "status": "opened",
                        },
                        "signers": sub.signers,
                    },
                )
                changed = True

        # Check if entire submission completed
        new_status = status_map.get(remote_status)
        if (
            new_status == ESigningSubmission.Status.COMPLETED
            and sub.status != ESigningSubmission.Status.COMPLETED
        ):
            self.stdout.write(
                self.style.SUCCESS(f"  Submission {ds_id} COMPLETED!")
            )
            sub.status = ESigningSubmission.Status.COMPLETED
            sub.signers = _sync_signer_statuses(sub.signers, submitters)

            signed_url = ""
            if documents:
                signed_url = documents[0].get("url", "")
            if signed_url:
                sub.signed_pdf_url = signed_url

            sub.webhook_payload = {
                "event_type": "submission.completed",
                "data": remote,
                "source": "poll_docuseal",
            }

            _activate_lease(sub)

            _broadcast_ws(
                sub.pk,
                {
                    "type": "submission_completed",
                    "submission_id": sub.pk,
                    "signed_pdf_url": sub.signed_pdf_url,
                    "signers": sub.signers,
                },
            )

            _notify_staff(sub, "submission.completed", remote)
            _email_signed_copy_to_signers(sub, remote)
            changed = True

        elif (
            new_status == ESigningSubmission.Status.DECLINED
            and sub.status != ESigningSubmission.Status.DECLINED
        ):
            self.stdout.write(
                self.style.WARNING(f"  Submission {ds_id} DECLINED")
            )
            sub.status = ESigningSubmission.Status.DECLINED
            _broadcast_ws(
                sub.pk,
                {
                    "type": "signer_declined",
                    "submission_id": sub.pk,
                    "signers": sub.signers,
                },
            )
            _notify_staff(sub, "submission.declined", remote)
            changed = True

        if changed:
            sub.save()
            self.stdout.write(
                f"  Updated submission {sub.pk} (docuseal {ds_id}) → {sub.status}"
            )
        else:
            self.stdout.write(f"  Submission {ds_id}: no changes (status={remote_status})")
