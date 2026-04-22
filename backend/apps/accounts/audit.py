from utils.http import get_client_ip
from .models import AuthAuditLog


def log_auth_event(event_type, request=None, user=None, metadata=None):
    """Log an immutable authentication audit event."""
    ip = ""
    ua = ""
    if request:
        ip = get_client_ip(request) or ""
        ua = request.META.get("HTTP_USER_AGENT", "")

    return AuthAuditLog.objects.create(
        user=user,
        event_type=event_type,
        ip_address=ip or None,
        user_agent=ua,
        metadata=metadata or {},
    )
