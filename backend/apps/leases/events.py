"""
Auto-generate lease calendar events and onboarding steps.
Called when a lease is created or activated.
"""
from datetime import timedelta
from dateutil.relativedelta import relativedelta

from .models import Lease, LeaseEvent, OnboardingStep


def generate_lease_events(lease: Lease) -> list[LeaseEvent]:
    """Generate all standard calendar events for a lease."""
    # Clear existing auto-generated events (keep custom ones)
    lease.events.exclude(event_type=LeaseEvent.EventType.CUSTOM).delete()

    events = []
    start = lease.start_date
    end = lease.end_date
    tenant_name = lease.primary_tenant.full_name if lease.primary_tenant else "Tenant"

    # 1. Contract Start
    events.append(LeaseEvent(
        lease=lease,
        event_type=LeaseEvent.EventType.CONTRACT_START,
        title=f"Lease starts — {tenant_name}",
        date=start,
    ))

    # 2. Deposit Due (7 days before start or on start)
    deposit_date = max(start - timedelta(days=7), start)
    events.append(LeaseEvent(
        lease=lease,
        event_type=LeaseEvent.EventType.DEPOSIT_DUE,
        title=f"Deposit due — R{lease.deposit:,.0f}",
        description=f"Deposit payment of R{lease.deposit:,.2f} due from {tenant_name}",
        date=deposit_date,
    ))

    # 3. Move-in Inspection
    events.append(LeaseEvent(
        lease=lease,
        event_type=LeaseEvent.EventType.INSPECTION_IN,
        title=f"Move-in inspection — {lease.unit}",
        date=start,
    ))

    # 4. First Rent Due (1st of month after start)
    if start.day == 1:
        first_rent = start
    else:
        first_rent = (start + relativedelta(months=1)).replace(day=1)
    events.append(LeaseEvent(
        lease=lease,
        event_type=LeaseEvent.EventType.FIRST_RENT,
        title=f"First rent due — R{lease.monthly_rent:,.0f}",
        date=first_rent,
    ))

    # 5. Monthly Rent Due (1st of each month for the lease period)
    current = first_rent + relativedelta(months=1)
    while current <= end:
        events.append(LeaseEvent(
            lease=lease,
            event_type=LeaseEvent.EventType.RENT_DUE,
            title=f"Rent due — R{lease.monthly_rent:,.0f}",
            date=current,
            is_recurring=True,
            recurrence_day=1,
        ))
        current += relativedelta(months=1)

    # 6. Routine Inspections (every 6 months from start)
    inspection_date = start + relativedelta(months=6)
    inspection_num = 1
    while inspection_date < end:
        events.append(LeaseEvent(
            lease=lease,
            event_type=LeaseEvent.EventType.INSPECTION_ROUTINE,
            title=f"Routine inspection #{inspection_num} — {lease.unit}",
            date=inspection_date,
        ))
        inspection_date += relativedelta(months=6)
        inspection_num += 1

    # 7. Notice Period Deadline
    notice_days = lease.notice_period_days or 20
    notice_date = end - timedelta(days=notice_days)
    if notice_date > start:
        events.append(LeaseEvent(
            lease=lease,
            event_type=LeaseEvent.EventType.NOTICE_DEADLINE,
            title=f"Notice deadline — {notice_days} days before end",
            description=f"Last day to give notice of non-renewal ({notice_days} business days)",
            date=notice_date,
        ))

    # 8. Renewal Review (60 days before end)
    renewal_date = end - timedelta(days=60)
    if renewal_date > start:
        events.append(LeaseEvent(
            lease=lease,
            event_type=LeaseEvent.EventType.RENEWAL_REVIEW,
            title=f"Renewal review — {tenant_name}",
            description="Review lease for renewal or termination",
            date=renewal_date,
        ))

    # 9. Move-out Inspection
    events.append(LeaseEvent(
        lease=lease,
        event_type=LeaseEvent.EventType.INSPECTION_OUT,
        title=f"Move-out inspection — {lease.unit}",
        date=end,
    ))

    # 10. Contract End
    events.append(LeaseEvent(
        lease=lease,
        event_type=LeaseEvent.EventType.CONTRACT_END,
        title=f"Lease ends — {tenant_name}",
        date=end,
    ))

    # Bulk create
    created = LeaseEvent.objects.bulk_create(events)
    return created


def generate_onboarding_steps(lease: Lease) -> list[OnboardingStep]:
    """Generate standard onboarding checklist for a new lease."""
    lease.onboarding_steps.all().delete()

    steps_config = [
        (OnboardingStep.StepType.LEASE_SIGNED, "Lease agreement signed", 1),
        (OnboardingStep.StepType.ID_VERIFIED, "Tenant ID verified", 2),
        (OnboardingStep.StepType.DEPOSIT_PAYMENT, f"Deposit paid — R{lease.deposit:,.0f}", 3),
        (OnboardingStep.StepType.INVOICING_SETUP, "Monthly invoicing configured", 4),
        (OnboardingStep.StepType.MOVE_IN_INSPECTION, "Move-in inspection completed", 5),
        (OnboardingStep.StepType.KEY_HANDOVER, "Keys handed over to tenant", 6),
        (OnboardingStep.StepType.TENANT_APP_SETUP, "Tenant registered on app", 7),
        (OnboardingStep.StepType.WELCOME_SENT, "Welcome message sent", 8),
    ]

    steps = [
        OnboardingStep(
            lease=lease,
            step_type=step_type,
            title=title,
            order=order,
        )
        for step_type, title, order in steps_config
    ]

    return OnboardingStep.objects.bulk_create(steps)
