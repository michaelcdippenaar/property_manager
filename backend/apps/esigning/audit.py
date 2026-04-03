from .models import ESigningAuditEvent


def log_esigning_event(submission, event_type, request=None, signer_role="", user=None, metadata=None):
    """Log an immutable audit event for e-signing compliance."""
    ip = ""
    ua = ""
    if request:
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        ip = xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR", "")
        ua = request.META.get("HTTP_USER_AGENT", "")

    return ESigningAuditEvent.objects.create(
        submission=submission,
        signer_role=signer_role,
        event_type=event_type,
        ip_address=ip or None,
        user_agent=ua,
        user=user,
        metadata=metadata or {},
    )
