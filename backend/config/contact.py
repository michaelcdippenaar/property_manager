"""
Public contact-form endpoint for klikk.co.za/contact.

Security posture:
- Origin-allowlisted (klikk.co.za + localhost in DEBUG).
- CSRF-exempt because it's a public cross-origin POST from the marketing
  site; protection is the origin allowlist + honeypot + IP rate limit.
- Honeypot field (``website``) — bots fill it, humans don't see it.
- Rate limit: max 5 submissions per IP per hour.

POPIA:
- Consent captured as ``consent_at`` timestamp (s11(1)(a) lawful basis).
- IP + user-agent retained for fraud/abuse; anonymise via admin action
  when retention window expires. See apps.contact.models.
"""
import json
import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.contact.models import ContactEnquiry
from utils.http import get_client_ip

logger = logging.getLogger(__name__)

ALLOWED_ORIGINS = {
    "https://klikk.co.za",
    "https://www.klikk.co.za",
}

RATE_LIMIT_PER_HOUR = 5


def _origin_allowed(request) -> bool:
    origin = request.META.get("HTTP_ORIGIN", "")
    if settings.DEBUG and origin.startswith("http://localhost"):
        return True
    return origin in ALLOWED_ORIGINS



@csrf_exempt
@require_POST
def contact_view(request):
    if not _origin_allowed(request):
        return JsonResponse({"error": "Forbidden"}, status=403)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # Honeypot: bots fill hidden fields. Humans don't see it, so any value = bot.
    if str(data.get("website", "")).strip():
        logger.info("Contact form honeypot triggered from %s", get_client_ip(request))
        # Pretend success so bots don't learn the trap exists.
        return JsonResponse({"ok": True})

    name = str(data.get("name", "")).strip()[:120]
    email = str(data.get("email", "")).strip()[:254]
    org = str(data.get("organisation", "")).strip()[:120]
    role = str(data.get("role", "")).strip()[:60] or "other"
    message = str(data.get("message", "")).strip()[:4000]
    consent = bool(data.get("consent"))

    if not name or not email or not message:
        return JsonResponse({"error": "name, email and message are required"}, status=400)

    if not consent:
        return JsonResponse(
            {"error": "POPIA consent is required to process this enquiry."},
            status=400,
        )

    ip_address = get_client_ip(request)
    user_agent = request.META.get("HTTP_USER_AGENT", "")[:512]

    # IP-based rate limit — best-effort, don't fail closed on DB errors.
    if ip_address:
        try:
            since = timezone.now() - timedelta(hours=1)
            recent = ContactEnquiry.objects.filter(
                ip_address=ip_address, created_at__gte=since
            ).count()
            if recent >= RATE_LIMIT_PER_HOUR:
                return JsonResponse(
                    {"error": "Too many enquiries. Please try again later."},
                    status=429,
                )
        except Exception:
            logger.exception("Rate-limit check failed; allowing through")

    # Validate role against model choices; fall back to "other" if unknown.
    valid_roles = {key for key, _ in ContactEnquiry.ROLE_CHOICES}
    if role not in valid_roles:
        role = "other"

    enquiry = ContactEnquiry.objects.create(
        name=name,
        email=email,
        organisation=org,
        role=role,
        message=message,
        consent_at=timezone.now() if consent else None,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    subject = f"[Klikk] Enquiry from {name}" + (f" ({org})" if org else "")
    body = (
        f"Name: {name}\n"
        f"Email: {email}\n"
        f"Organisation: {org or '—'}\n"
        f"Role: {role}\n"
        f"IP: {ip_address or '—'}\n"
        f"\nMessage:\n{message}\n"
        f"\n—\nEnquiry ID: {enquiry.pk}\n"
        f"Review: /admin/contact/contactenquiry/{enquiry.pk}/change/"
    )

    recipient = getattr(settings, "CONTACT_EMAIL", "mc@klikk.co.za")

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
    except Exception:
        logger.exception(
            "Failed to send contact form email (enquiry id=%s) from %s",
            enquiry.pk,
            email,
        )
        # Record persisted; admin can still see it. Tell the user to email.
        return JsonResponse(
            {"error": "Could not send message. Please email us directly."},
            status=500,
        )

    enquiry.email_sent = True
    enquiry.save(update_fields=["email_sent"])

    return JsonResponse({"ok": True})
