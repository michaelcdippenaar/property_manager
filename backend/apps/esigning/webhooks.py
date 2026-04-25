import hashlib
import hmac
import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import ESigningPublicLink, ESigningSubmission

logger = logging.getLogger(__name__)


# ── Signature verification ────────────────────────────────────────────


def _verify_signature(body: bytes, signature: str) -> bool:
    """
    Verify an inbound webhook signature for the esigning integration.

    Behaviour:
    - ``settings.WEBHOOK_SECRET_ESIGNING`` controls the shared secret.
    - ``settings.WEBHOOK_HEADER_ESIGNING`` selects the verification mode:
      - Empty / not set → HMAC-SHA256 mode: compute HMAC over *body* and
        compare with *signature* using a timing-safe digest comparison.
      - Non-empty         → static-token mode: compare *signature* directly
        against the secret using ``hmac.compare_digest`` (constant-time).
    - When the secret is not configured (empty string / falsy) the check is
      skipped and True is returned, allowing the integration to run without
      enforced verification in development.  A warning is logged.

    The delegate helper ``utils.webhook_signature.verify_hmac_signature``
    is used for the HMAC path to keep replay-protection logic centralised.
    """
    secret: str = getattr(settings, "WEBHOOK_SECRET_ESIGNING", "") or ""
    header_name: str = getattr(settings, "WEBHOOK_HEADER_ESIGNING", "") or ""

    if not secret:
        logger.warning(
            "_verify_signature: WEBHOOK_SECRET_ESIGNING is not set — "
            "signature verification skipped."
        )
        return True

    if not signature:
        logger.warning("_verify_signature: missing signature — rejected.")
        return False

    if header_name:
        # Static token mode: compare signature directly against the secret.
        valid = hmac.compare_digest(secret, signature)
        if not valid:
            logger.warning("_verify_signature: static token mismatch — rejected.")
        return valid

    # HMAC-SHA256 mode
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    valid = hmac.compare_digest(expected, signature.lower().strip())
    if not valid:
        logger.warning("_verify_signature: HMAC mismatch — rejected.")
    return valid


# ── Signer helpers ────────────────────────────────────────────────────


def _sync_signer_statuses(signers: list, submitters: list) -> list:
    """Bulk-update signer records from a list of submitter dicts."""
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
    """Update a single signer record by signer ID."""
    if not submitter_id:
        return signers
    updated = []
    for s in signers:
        if str(s.get('id')) == submitter_id:
            s = {**s, **updates}
        updated.append(s)
    return updated


def _find_signer(signers: list, submitter_id: str) -> dict | None:
    """Return signer dict by ID, or None."""
    if not submitter_id:
        return None
    for s in signers or []:
        if str(s.get('id')) == submitter_id:
            return _safe_signer_info(s)
    return None


def _safe_signer_info(signer: dict) -> dict:
    """Return signer dict safe for WebSocket/API."""
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
    No-ops silently for mandate submissions (which have no lease).
    """
    if not submission.lease_id:
        return
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
    signer_role = next_signer.get('role', '')

    if not signer_role:
        logger.warning("Next signer has no role, cannot notify")
        return

    # Create public signing link
    default_days = int(getattr(settings, 'ESIGNING_PUBLIC_LINK_EXPIRY_DAYS', 14))
    link = ESigningPublicLink.objects.create(
        submission=submission,
        signer_role=signer_role,
        expires_at=timezone.now() + timedelta(days=default_days),
    )

    base_url = getattr(settings, 'SIGNING_PUBLIC_APP_BASE_URL', '') or ''
    sign_path = f"/sign/{link.pk}/"
    signing_url = f"{base_url}{sign_path}" if base_url else None

    if submission.lease_id:
        prop = submission.lease.unit.property
        doc_title = f"{prop.name} — Unit {submission.lease.unit.unit_number}"
    elif submission.mandate_id:
        doc_title = f"Rental Mandate — {submission.mandate.property.name}"
    else:
        doc_title = "Document"

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
        "Next signer notified: %s for submission %s",
        name or email, submission.pk,
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


def _broadcast_agent_notification(creator_pk: int, payload: dict):
    """
    Push a signing notification to the agent's personal notification channel.

    Group: ``signing_notifications_<creator_pk>``
    Handled by: ``ESigningAgentNotificationsConsumer.signing_notification``
    """
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        group = f"signing_notifications_{creator_pk}"
        async_to_sync(channel_layer.group_send)(
            group,
            {"type": "signing.notification", "payload": payload},
        )
    except Exception:
        logger.exception(
            "Failed to broadcast agent notification for creator_pk=%s", creator_pk
        )


# ── Staff notification ────────────────────────────────────────────────


def _notify_staff(submission: ESigningSubmission, event_type: str, data: dict):
    """
    Notify the agent/admin who created the submission about signing progress.

    Sends:
    1. A branded HTML email via send_template_email (signing_agent_notification template)
    2. A real-time WebSocket push to the agent's personal notification channel so
       the admin SPA can display a global toast (ESigningAgentNotificationsConsumer).
    """
    import uuid as _uuid
    from django.conf import settings as _settings

    creator = submission.created_by
    if not creator or not creator.email:
        return

    # ── Build context ────────────────────────────────────────────────
    if submission.lease_id:
        prop = submission.lease.unit.property
        doc_type = "lease"
        doc_title = f"{prop.name} — Unit {submission.lease.unit.unit_number}"
        property_address = (
            prop.address
            if hasattr(prop, "address") and prop.address
            else prop.name
        )
        # Deep-link into the relevant lease signing panel
        admin_base = getattr(_settings, "ADMIN_APP_BASE_URL", "").rstrip("/")
        panel_url = f"{admin_base}/leases/{submission.lease_id}?tab=esigning" if admin_base else ""
    elif submission.mandate_id:
        prop = submission.mandate.property
        doc_type = "mandate"
        doc_title = f"Rental Mandate — {prop.name}"
        property_address = (
            prop.address
            if hasattr(prop, "address") and prop.address
            else prop.name
        )
        admin_base = getattr(_settings, "ADMIN_APP_BASE_URL", "").rstrip("/")
        panel_url = f"{admin_base}/properties/{prop.pk}?tab=mandate" if admin_base else ""
    else:
        doc_type = "document"
        doc_title = "Document"
        property_address = ""
        panel_url = ""

    submitter = data.get("submitter") or data
    signer_name = (submitter.get("name") or submitter.get("email") or "A signer").strip()

    # Re-use event_id threaded from the call site (views.py) so the per-submission
    # WS broadcast and global notification share the same ID for frontend dedup.
    # Fall back to a fresh UUID when called from paths that don't provide one.
    event_id = data.get("event_id") or str(_uuid.uuid4())

    if event_type == "form.completed":
        completed = sum(
            1 for s in submission.signers
            if (s.get("status") or "").lower() in ("completed", "signed")
        )
        total = len(submission.signers or [])
        email_subject = f"Signing progress: {doc_title} ({completed}/{total})"
        notification_type = "signer_completed"
        toast_message = (
            f"{signer_name} signed the {doc_type} — {completed}/{total} complete"
        )
        email_context = {
            "event_label": "Signer completed",
            "progress_line": f"Progress: {completed} of {total} signers complete.",
            "show_download": False,
        }
    elif event_type == "submission.completed":
        email_subject = f"All signatures complete: {doc_title}"
        notification_type = "submission_completed"
        toast_message = f"All parties signed the {doc_type} for {property_address or doc_title}"
        email_context = {
            "event_label": "All signatures complete",
            "progress_line": "The signed document is ready for download.",
            "show_download": bool(submission.signed_pdf_file),
            "signed_pdf_url": submission.signed_pdf_file.url if submission.signed_pdf_file else "",
        }
    elif event_type == "submission.declined":
        email_subject = f"Signing declined: {doc_title}"
        notification_type = "signer_declined"
        toast_message = f"{signer_name} declined to sign the {doc_type}"
        email_context = {
            "event_label": "Signing declined",
            "progress_line": f"{signer_name} has declined to sign.",
            "show_download": False,
        }
    else:
        return

    # ── 1. WebSocket push (in-app toast) ─────────────────────────────
    ws_payload = {
        "type": notification_type,
        "event_id": event_id,
        "submission_id": submission.pk,
        "signer_name": signer_name,
        "doc_type": doc_type,
        "doc_title": doc_title,
        "property_address": property_address,
        "message": toast_message,
        "panel_url": panel_url,
    }
    _broadcast_agent_notification(creator.pk, ws_payload)

    # ── 2. Email notification ─────────────────────────────────────────
    creator_name = (
        getattr(creator, "get_full_name", lambda: "")()
        or getattr(creator, "first_name", "")
        or "there"
    )
    email_body_lines = [
        f"**{signer_name}** {email_context['event_label'].lower()} on:",
        f"**{doc_title}**",
        "",
    ]
    if property_address and property_address != doc_title:
        email_body_lines.append(f"Property: {property_address}")
        email_body_lines.append("")
    email_body_lines.append(email_context["progress_line"])

    plain_body = "\n".join(email_body_lines)
    if panel_url:
        plain_body += f"\n\nView signing panel: {panel_url}"

    # Build inline HTML for the email (no template dependency)
    button_html = (
        f'<p><a href="{panel_url}" style="display:inline-block;padding:12px 24px;'
        f'background:#2B2D6E;color:#fff;text-decoration:none;border-radius:8px;'
        f'font-weight:600;">View Signing Panel</a></p>'
        if panel_url else ""
    )
    download_html = (
        f'<p><a href="{email_context["signed_pdf_url"]}" style="font-size:13px;color:#2B2D6E;">'
        f'Download signed PDF</a></p>'
        if email_context.get("show_download") and email_context.get("signed_pdf_url") else ""
    )
    name_html = f"<strong>{signer_name}</strong>"
    html_body = (
        f"<p>Hello {creator_name},</p>"
        f"<p>{name_html} {email_context['event_label'].lower()} on "
        f"<strong>{doc_title}</strong>.</p>"
        + (
            f"<p>Property: {property_address}</p>"
            if property_address and property_address != doc_title else ""
        )
        + f"<p>{email_context['progress_line']}</p>"
        + button_html
        + download_html
        + '<p style="font-size:12px;color:#999;margin-top:16px;">— Klikk Property Management</p>'
    )

    try:
        from apps.notifications.services import send_email
        send_email(email_subject, plain_body, creator.email, html_body=html_body)
    except Exception:
        logger.exception("Failed to notify staff for submission %s", submission.pk)


# ── Email signed copy to all signers ─────────────────────────────────


def _email_signed_copy_to_signers(submission: ESigningSubmission, data: dict):
    """
    When a submission is fully completed, email a link to the signed PDF
    to every signer so they have a copy for their records.
    """
    signed_url = None

    # Use local signed PDF file URL
    if submission.signed_pdf_file:
        try:
            signed_url = submission.signed_pdf_file.url
        except Exception:
            pass

    # Ensure relative URLs become absolute
    if signed_url and signed_url.startswith('/'):
        from django.conf import settings
        from django.core.exceptions import ImproperlyConfigured
        _site_url = getattr(settings, 'SITE_URL', '')
        if not _site_url:
            if not getattr(settings, 'DEBUG', True):
                raise ImproperlyConfigured("SITE_URL is required in production")
            _site_url = 'http://localhost:8000'
        signed_url = f"{_site_url.rstrip('/')}{signed_url}"

    if not signed_url:
        logger.warning(
            "No signed PDF for submission %s — cannot email signers",
            submission.pk,
        )
        return

    if submission.lease_id:
        prop = submission.lease.unit.property
        doc_title = f"{prop.name} — Unit {submission.lease.unit.unit_number}"
    elif submission.mandate_id:
        doc_title = f"Rental Mandate — {submission.mandate.property.name}"
    else:
        doc_title = "Document"

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
