"""
Maintenance beat tasks.

Registered in CELERY_BEAT_SCHEDULE (see backend/core/settings.py or celery.py).

Task: escalate_overdue_maintenance
  Runs hourly. Finds tickets that:
    - are still open or in_progress
    - have breached their sla_resolve_deadline by more than 48 hours
    - have not yet been escalated (sla_escalated=False)
  Sends an email to every agency_admin for the relevant agency, then sets
  sla_escalated=True so the email is not sent again.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from django.utils import timezone

logger = logging.getLogger(__name__)


def escalate_overdue_maintenance():
    """
    Escalate maintenance tickets overdue by >48h to the agency admin.

    Safe to call directly (no Celery dependency).  When Celery is wired up,
    wrap with @shared_task and add to CELERY_BEAT_SCHEDULE.
    """
    from apps.maintenance.models import MaintenanceRequest

    threshold = timezone.now() - timedelta(hours=48)

    tickets = MaintenanceRequest.objects.filter(
        sla_resolve_deadline__lt=threshold,
        status__in=[MaintenanceRequest.Status.OPEN, MaintenanceRequest.Status.IN_PROGRESS],
        sla_escalated=False,
    ).select_related("unit__property", "tenant")

    escalated_ids: list[int] = []

    for ticket in tickets:
        try:
            _send_escalation_email(ticket)
            escalated_ids.append(ticket.pk)
        except Exception:
            logger.exception("Escalation email failed for ticket #%s", ticket.pk)

    if escalated_ids:
        MaintenanceRequest.objects.filter(pk__in=escalated_ids).update(sla_escalated=True)
        logger.info("Escalated %d overdue maintenance tickets: %s", len(escalated_ids), escalated_ids)

    return len(escalated_ids)


def _send_escalation_email(ticket: "MaintenanceRequest") -> None:
    """Send an escalation notification email to agency admins."""
    from django.core.mail import send_mail
    from django.conf import settings
    from apps.accounts.models import User, Agency

    # Resolve the agency for this ticket (via property → agency)
    agency = None
    try:
        agency = ticket.unit.property.agency
    except Exception:
        pass

    if agency:
        admins = User.objects.filter(agency=agency, role__in=["agency_admin", "admin"], is_active=True)
    else:
        admins = User.objects.filter(role__in=["agency_admin", "admin"], is_active=True)

    recipient_emails = list(admins.values_list("email", flat=True))
    if not recipient_emails:
        logger.warning(
            "No agency admin emails found for escalation of ticket #%s", ticket.pk
        )
        return

    hours_overdue = (timezone.now() - ticket.sla_resolve_deadline).total_seconds() / 3600

    subject = f"[ESCALATION] Maintenance ticket #{ticket.pk} is {hours_overdue:.0f}h overdue"
    body = (
        f"Maintenance ticket #{ticket.pk} requires urgent attention.\n\n"
        f"Title: {ticket.title}\n"
        f"Priority: {ticket.get_priority_display()}\n"
        f"Status: {ticket.get_status_display()}\n"
        f"SLA resolve deadline: {ticket.sla_resolve_deadline.strftime('%d %b %Y %H:%M')}\n"
        f"Hours overdue: {hours_overdue:.1f}h\n"
        f"Property: {ticket.unit.property}\n"
        f"Unit: {ticket.unit}\n"
    )
    if ticket.tenant:
        body += f"Tenant: {ticket.tenant.full_name}\n"

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@klikk.co.za")
    send_mail(subject, body, from_email, recipient_emails, fail_silently=False)
    logger.info(
        "Escalation email sent for ticket #%s to: %s", ticket.pk, recipient_emails
    )
