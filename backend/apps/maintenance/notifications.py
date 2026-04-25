"""
Notification service for supplier job dispatch (SMS + WhatsApp via apps.notifications).
"""
import logging

from django.conf import settings

from apps.notifications.services import notify_sms_and_whatsapp

logger = logging.getLogger(__name__)


def notify_supplier(quote_request):
    """
    Send job notification to supplier via SMS and WhatsApp (Twilio when configured).
    Returns True if at least one channel succeeded.
    """
    base_url = getattr(settings, "BASE_URL", "")
    token = quote_request.token
    supplier = quote_request.supplier
    job = quote_request.dispatch.maintenance_request

    url = f"{base_url}/quote/{token}"
    message = (
        f"New job request: {job.title}\n"
        f"Priority: {job.priority}\n"
        f"Quote here: {url}"
    )

    if not (supplier.phone or "").strip():
        logger.warning("notify_supplier: supplier %s has no phone", supplier.pk)
        return False

    results = notify_sms_and_whatsapp(supplier.phone, message)
    ok = any(results.values())
    if not ok:
        logger.info(
            "[NOTIFY] No channel delivered (configure Twilio). To: %s (%s)\n%s",
            supplier.phone,
            supplier.display_name,
            message,
        )
    return ok
