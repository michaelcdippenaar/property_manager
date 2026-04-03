import hashlib
import hmac
import json
import logging
from datetime import timedelta

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .models import ESigningPublicLink, ESigningSubmission

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class DocuSealWebhookView(View):
    """
    POST /api/v1/esigning/webhook/
    DocuSeal sends events here. We update submission status accordingly,
    broadcast real-time updates via WebSocket, and — for sequential signing —
    notify the next signer when the previous one completes.
    """

    def get(self, request):
        """Reachability check from browser or uptime tools; DocuSeal still must POST events."""
        return JsonResponse({
            'detail': 'Tremly DocuSeal webhook receiver. Configure POST URL in DocuSeal to this path.',
        })

    def head(self, request):
        return HttpResponse(status=200)

    def post(self, request):
        secret = (getattr(settings, 'DOCUSEAL_WEBHOOK_SECRET', '') or '').strip()
        header_name = (getattr(settings, 'DOCUSEAL_WEBHOOK_HEADER_NAME', '') or '').strip()
        if secret:
            if header_name:
                incoming = request.headers.get(header_name, '')
                if not incoming or not hmac.compare_digest(incoming, secret):
                    return HttpResponse('Invalid webhook secret header', status=400)
            else:
                sig = request.headers.get('X-Docuseal-Signature', '')
                expected = hmac.new(secret.encode(), request.body, hashlib.sha256).hexdigest()
                if not hmac.compare_digest(sig, expected):
                    return HttpResponse('Invalid signature', status=400)

        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return HttpResponse('Bad JSON', status=400)

        event_type = payload.get('event_type', '')
        data       = payload.get('data', {})

        logger.info("DocuSeal webhook: %s", event_type)

        submission_id = (
            data.get('submission_id') or
            data.get('submission', {}).get('id') or
            data.get('id', '')
        )
        if not submission_id:
            return HttpResponse('ok')

        try:
            obj = ESigningSubmission.objects.select_related(
                'lease__unit__property',
            ).get(docuseal_submission_id=str(submission_id))
        except ESigningSubmission.DoesNotExist:
            return HttpResponse('ok')

        obj.webhook_payload = payload
        ws_event = None  # Will be broadcast after save

        if event_type == 'submission.completed':
            obj.status = ESigningSubmission.Status.COMPLETED
            # Prefer the actual signed document over the audit log
            signed_url = (
                data.get('documents', [{}])[0].get('url', '')
                or data.get('audit_log_url', '')
            )
            if signed_url:
                obj.signed_pdf_url = signed_url
            obj.signers = _sync_signer_statuses(obj.signers, data.get('submitters', []))

            # Activate the lease now that all parties have signed
            _activate_lease(obj)

            ws_event = {
                'type': 'submission_completed',
                'submission_id': obj.pk,
                'signed_pdf_url': obj.signed_pdf_url,
                'signers': obj.signers,
            }

        elif event_type == 'form.completed':
            submitter = data.get('submitter') or data
            submitter_id = str(submitter.get('id', ''))
            obj.signers = _update_single_signer(obj.signers, submitter_id, {
                'status': 'completed',
                'completed_at': submitter.get('completed_at'),
            })
            if obj.status == ESigningSubmission.Status.PENDING:
                obj.status = ESigningSubmission.Status.IN_PROGRESS

            # Determine who just signed
            completed_signer = _find_signer(obj.signers, submitter_id)

            # In sequential mode, notify the next signer
            next_signer = None
            if obj.signing_mode == ESigningSubmission.SigningMode.SEQUENTIAL:
                next_signer = _get_next_signer(obj.signers)
                if next_signer:
                    _notify_next_signer(obj, next_signer)

            ws_event = {
                'type': 'signer_completed',
                'submission_id': obj.pk,
                'completed_signer': completed_signer,
                'next_signer': _safe_signer_info(next_signer) if next_signer else None,
                'completed_count': sum(
                    1 for s in obj.signers
                    if (s.get('status') or '').lower() in ('completed', 'signed')
                ),
                'total_signers': len(obj.signers or []),
                'signers': obj.signers,
            }

        elif event_type == 'submission.declined':
            obj.status = ESigningSubmission.Status.DECLINED
            submitter = data.get('submitter') or {}
            submitter_id = str(submitter.get('id', ''))
            if submitter_id:
                obj.signers = _update_single_signer(obj.signers, submitter_id, {
                    'status': 'declined',
                })
            ws_event = {
                'type': 'signer_declined',
                'submission_id': obj.pk,
                'declined_signer': _find_signer(obj.signers, submitter_id),
                'signers': obj.signers,
            }

        elif event_type in ('form.viewed', 'form.started'):
            if obj.status == ESigningSubmission.Status.PENDING:
                obj.status = ESigningSubmission.Status.IN_PROGRESS
            submitter = data.get('submitter') or data
            submitter_id = str(submitter.get('id', ''))
            if submitter_id:
                obj.signers = _update_single_signer(obj.signers, submitter_id, {
                    'status': 'opened',
                })
            ws_event = {
                'type': 'signer_viewed',
                'submission_id': obj.pk,
                'signer': _find_signer(obj.signers, submitter_id),
                'signers': obj.signers,
            }

        obj.save()

        # Broadcast via WebSocket
        if ws_event:
            _broadcast_ws(obj.pk, ws_event)

        # Notify agent/admin who created the submission
        if event_type in ('form.completed', 'submission.completed', 'submission.declined'):
            _notify_staff(obj, event_type, data)

        # Email signed copy to all signers when fully completed
        if event_type == 'submission.completed':
            _email_signed_copy_to_signers(obj, data)

        return HttpResponse('ok')


# ── Signer helpers ────────────────────────────────────────────────────


def _sync_signer_statuses(signers: list, submitters: list) -> list:
    """Bulk-update signer records from a list of DocuSeal submitters."""
    updated = []
    for s in signers:
        matching = next(
            (x for x in submitters if str(x.get('id')) == str(s.get('id'))),
            None,
        )
        if matching:
            s = {
                **s,
                'status': matching.get('status', s.get('status')),
                'completed_at': matching.get('completed_at'),
            }
        updated.append(s)
    return updated or signers


def _update_single_signer(signers: list, submitter_id: str, updates: dict) -> list:
    """Update a single signer record by DocuSeal submitter ID."""
    if not submitter_id:
        return signers
    updated = []
    for s in signers:
        if str(s.get('id')) == submitter_id:
            s = {**s, **updates}
        updated.append(s)
    return updated


def _find_signer(signers: list, submitter_id: str) -> dict | None:
    """Return signer dict by submitter ID, or None."""
    if not submitter_id:
        return None
    for s in signers or []:
        if str(s.get('id')) == submitter_id:
            return _safe_signer_info(s)
    return None


def _safe_signer_info(signer: dict) -> dict:
    """Return signer dict safe for WebSocket/API (no embed_src leak)."""
    return {
        'id': signer.get('id'),
        'name': signer.get('name', ''),
        'email': signer.get('email', ''),
        'role': signer.get('role', ''),
        'status': signer.get('status', ''),
        'order': signer.get('order', 0),
        'completed_at': signer.get('completed_at'),
    }


def _get_next_signer(signers: list) -> dict | None:
    """
    For sequential signing: return the first signer whose status is not
    completed/signed/declined. Signers are already sorted by order.
    """
    for s in signers or []:
        st = (s.get('status') or '').lower()
        if st not in ('completed', 'signed', 'declined'):
            return s
    return None


def _activate_lease(submission: ESigningSubmission):
    """
    When all parties have signed, transition the lease from 'pending' to 'active'.
    Only activates if the lease is currently pending — won't override other statuses.
    """
    try:
        from apps.leases.models import Lease
        lease = submission.lease
        if lease.status == Lease.Status.PENDING:
            lease.status = Lease.Status.ACTIVE
            lease.save(update_fields=['status'])
            logger.info(
                "Lease pk=%s activated after signing submission pk=%s completed",
                lease.pk, submission.pk,
            )
    except Exception:
        logger.exception(
            "Failed to activate lease for submission pk=%s", submission.pk,
        )


# ── Next-signer notification (sequential mode) ───────────────────────


def _notify_next_signer(submission: ESigningSubmission, next_signer: dict):
    """
    When the previous signer completes in sequential mode:
    1. Create a public signing link for the next signer
    2. Send email notification with signing link
    3. Send SMS/WhatsApp if phone available
    """
    email = (next_signer.get('email') or '').strip()
    name = (next_signer.get('name') or '').strip()
    submitter_id = next_signer.get('id')

    if not submitter_id:
        logger.warning("Next signer has no submitter ID, cannot notify")
        return

    # Create public signing link
    default_days = int(getattr(settings, 'ESIGNING_PUBLIC_LINK_EXPIRY_DAYS', 14))
    link = ESigningPublicLink.objects.create(
        submission=submission,
        submitter_id=int(submitter_id),
        signer_role=next_signer.get('role', ''),
        expires_at=timezone.now() + timedelta(days=default_days),
    )

    base_url = getattr(settings, 'SIGNING_PUBLIC_APP_BASE_URL', '') or ''
    sign_path = f"/sign/{link.pk}/"
    signing_url = f"{base_url}{sign_path}" if base_url else None

    prop = submission.lease.unit.property
    doc_title = f"{prop.name} — Unit {submission.lease.unit.unit_number}"

    # Email notification
    if email and signing_url:
        try:
            from apps.notifications.services import send_email

            salutation = f"Hello {name}," if name else "Hello,"
            exp = link.expires_at.strftime("%d %b %Y")

            # Detect landlord role for tailored messaging
            role = (next_signer.get('role') or '').lower()
            is_landlord = role in ('landlord', 'lessor', 'owner')

            if is_landlord:
                subject = f"All tenants signed — your signature needed: {doc_title}"
                intro_plain = (
                    "All tenants have completed signing the lease agreement. "
                    "Please review and add your signature as landlord to finalise the document."
                )
                intro_html = (
                    "All tenants have completed signing the lease agreement. "
                    "Please review and add <strong>your signature as landlord</strong> to finalise the document."
                )
            else:
                subject = f"Your turn to sign: {doc_title}"
                intro_plain = (
                    "The previous signer has completed their part. "
                    "It is now your turn to review and sign the document."
                )
                intro_html = (
                    "The previous signer has completed their part. "
                    "It is now <strong>your turn</strong> to review and sign."
                )

            plain = (
                f"{salutation}\n\n"
                f"{intro_plain}\n\n"
                f"Please sign using this link:\n{signing_url}\n\n"
                f"This link expires on {exp}.\n\n"
                f"If you did not expect this email, you can ignore it.\n"
            )
            html = (
                f"<p>{salutation}</p>"
                f"<p>{intro_html}</p>"
                f'<p><a href="{signing_url}" style="display:inline-block;padding:12px 20px;'
                f'background:#1e3a5f;color:#fff;text-decoration:none;border-radius:8px;'
                f'font-weight:600;">Sign now</a></p>'
                f'<p style="font-size:13px;color:#666;">'
                f'<a href="{signing_url}">{signing_url}</a></p>'
                f'<p style="font-size:12px;color:#999;">This link expires on {exp}.</p>'
            )
            send_email(subject, plain, email, html_body=html)
        except Exception:
            logger.exception("Failed to send next-signer email for submission %s", submission.pk)

    # SMS/WhatsApp notification (if phone on signer record)
    phone = (next_signer.get('phone') or '').strip()
    if phone and signing_url:
        try:
            from apps.notifications.services import notify_sms_and_whatsapp

            sms_body = (
                f"It's your turn to sign: {doc_title}. "
                f"Open this link to sign: {signing_url}"
            )
            notify_sms_and_whatsapp(phone, sms_body)
        except Exception:
            logger.exception("Failed to send next-signer SMS for submission %s", submission.pk)

    logger.info(
        "Next signer notified: %s (submitter %s) for submission %s",
        name or email, submitter_id, submission.pk,
    )


# ── WebSocket broadcast ──────────────────────────────────────────────


def _broadcast_ws(submission_pk: int, event: dict):
    """Send event to all WebSocket subscribers for this submission."""
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        group = f"esigning_{submission_pk}"
        async_to_sync(channel_layer.group_send)(
            group,
            {"type": "esigning.update", "payload": event},
        )
    except Exception:
        logger.exception("Failed to broadcast WebSocket event for submission %s", submission_pk)


# ── Staff notification ────────────────────────────────────────────────


def _notify_staff(submission: ESigningSubmission, event_type: str, data: dict):
    """
    Notify the agent/admin who created the submission about signing progress.
    Uses email. Push notifications can be added when FCM is configured.
    """
    creator = submission.created_by
    if not creator or not creator.email:
        return

    prop = submission.lease.unit.property
    doc_title = f"{prop.name} — Unit {submission.lease.unit.unit_number}"

    submitter = data.get('submitter') or data
    signer_name = submitter.get('name') or submitter.get('email', 'A signer')

    if event_type == 'form.completed':
        completed = sum(
            1 for s in submission.signers
            if (s.get('status') or '').lower() in ('completed', 'signed')
        )
        total = len(submission.signers or [])
        subject = f"Signing progress: {doc_title} ({completed}/{total})"
        body = (
            f"{signer_name} has signed the document for {doc_title}.\n"
            f"Progress: {completed} of {total} signers complete."
        )
    elif event_type == 'submission.completed':
        subject = f"All signatures complete: {doc_title}"
        body = (
            f"All signers have completed signing for {doc_title}.\n"
            f"The signed document is ready for download."
        )
        if submission.signed_pdf_url:
            body += f"\n\nSigned PDF: {submission.signed_pdf_url}"
    elif event_type == 'submission.declined':
        subject = f"Signing declined: {doc_title}"
        body = f"{signer_name} has declined to sign the document for {doc_title}."
    else:
        return

    try:
        from apps.notifications.services import send_email
        send_email(subject, body, creator.email)
    except Exception:
        logger.exception("Failed to notify staff for submission %s", submission.pk)


# ── Email signed copy to all signers ─────────────────────────────────


def _email_signed_copy_to_signers(submission: ESigningSubmission, data: dict):
    """
    When a submission is fully completed, email a link to the signed PDF
    to every signer so they have a copy for their records.

    DocuSeal file URLs contain time-limited tokens, so we fetch a fresh
    URL from the API to ensure the download link in the email works.
    """
    from . import services as esigning_services

    signed_url = None

    # Fetch fresh URL from DocuSeal API (most reliable)
    docuseal_id = submission.docuseal_submission_id
    if docuseal_id:
        try:
            sub_data = esigning_services._docuseal_get(f'/submissions/{docuseal_id}')
            docs = sub_data.get('documents') or []
            if docs:
                signed_url = docs[0].get('url', '')
        except Exception:
            logger.warning("Could not fetch fresh signed URL from DocuSeal for submission %s", submission.pk)

    # Fallback: use webhook data or stored URL
    if not signed_url:
        docs = data.get('documents') or []
        if docs:
            signed_url = docs[0].get('url', '')
    if not signed_url:
        signed_url = submission.signed_pdf_url
    if not signed_url:
        logger.warning(
            "No signed PDF URL for submission %s — cannot email signers",
            submission.pk,
        )
        return

    prop = submission.lease.unit.property
    doc_title = f"{prop.name} — Unit {submission.lease.unit.unit_number}"

    for signer in submission.signers or []:
        email = (signer.get('email') or '').strip()
        name = (signer.get('name') or '').strip()
        if not email:
            continue

        salutation = f"Hello {name}," if name else "Hello,"
        subject = f"Your signed copy: {doc_title}"
        plain = (
            f"{salutation}\n\n"
            f"All parties have signed the document for {doc_title}.\n\n"
            f"You can download your signed copy here:\n{signed_url}\n\n"
            f"Please save this for your records.\n\n"
            f"Thank you,\nTremly Property Management\n"
        )
        html = (
            f"<p>{salutation}</p>"
            f"<p>All parties have signed the document for "
            f"<strong>{doc_title}</strong>.</p>"
            f'<p><a href="{signed_url}" style="display:inline-block;padding:12px 20px;'
            f'background:#1e3a5f;color:#fff;text-decoration:none;border-radius:8px;'
            f'font-weight:600;">Download Signed Document</a></p>'
            f'<p style="font-size:13px;color:#666;">'
            f'<a href="{signed_url}">{signed_url}</a></p>'
            f'<p style="font-size:12px;color:#999;">Please save this document for your records.</p>'
            f'<p style="margin-top:16px;font-size:12px;color:#999;">— Tremly Property Management</p>'
        )

        try:
            from apps.notifications.services import send_email
            send_email(subject, plain, email, html_body=html)
            logger.info(
                "Sent signed copy to signer %s (%s) for submission %s",
                name, email, submission.pk,
            )
        except Exception:
            logger.exception(
                "Failed to email signed copy to %s for submission %s",
                email, submission.pk,
            )
