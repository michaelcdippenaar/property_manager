"""
Notification service for supplier job dispatch.
Currently logs to console — ready for SMS/WhatsApp integration.
"""
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def notify_supplier(quote_request):
    """
    Send job notification to supplier via SMS/WhatsApp.
    Returns True if notification was sent successfully.
    """
    base_url = getattr(settings, "BASE_URL", "http://localhost:5175")
    token = quote_request.token
    supplier = quote_request.supplier
    job = quote_request.dispatch.maintenance_request

    url = f"{base_url}/quote/{token}"
    message = (
        f"New job request: {job.title}\n"
        f"Priority: {job.priority}\n"
        f"Quote here: {url}"
    )

    # TODO: Integrate Twilio / WhatsApp Business API
    # For now, log the notification
    logger.info(
        f"[NOTIFY] To: {supplier.phone} ({supplier.display_name})\n"
        f"  Message: {message}"
    )

    # Print to console for development visibility
    print(f"\n{'='*50}")
    print(f"SUPPLIER NOTIFICATION")
    print(f"To: {supplier.phone} ({supplier.display_name})")
    print(f"Job: {job.title}")
    print(f"Link: {url}")
    print(f"{'='*50}\n")

    return True
