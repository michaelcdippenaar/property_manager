from utils.http import get_client_ip
from .models import ESigningAuditEvent


def log_esigning_event(submission, event_type, request=None, signer_role="", user=None, metadata=None):
    """Log an immutable audit event for e-signing compliance."""
    ip = ""
    ua = ""
    if request:
        ip = get_client_ip(request) or ""
        ua = request.META.get("HTTP_USER_AGENT", "")

    return ESigningAuditEvent.objects.create(
        submission=submission,
        agency_id=getattr(submission, "agency_id", None),
        signer_role=signer_role,
        event_type=event_type,
        ip_address=ip or None,
        user_agent=ua,
        user=user,
        metadata=metadata or {},
    )
