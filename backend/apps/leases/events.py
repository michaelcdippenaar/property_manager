"""Auto-generate LeaseEvent and OnboardingStep records for a lease."""
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from .models import Lease, LeaseEvent, OnboardingStep

E = LeaseEvent.EventType
S = LeaseEvent.Status


def _first_of_next_month(d: date) -> date:
    """Return the 1st of the month after `d`."""
    return (d.replace(day=1) + relativedelta(months=1))


def generate_lease_events(lease: Lease) -> None:
    """
    Create all standard calendar events for `lease`.
    Idempotent for non-recurring events (skips if already exists by type).
    Rent-due events are always regenerated fresh.
    """
    # Delete existing auto-generated events (not custom ones)
    lease.events.exclude(event_type=E.CUSTOM).delete()

    start = lease.start_date
    end = lease.end_date
    notice = lease.notice_period_days or 20

    events = []

    # 1. Deposit Due — 7 days before start (or on start)
    deposit_date = max(start - timedelta(days=7), start)
    events.append(LeaseEvent(
        lease=lease,
        event_type=E.DEPOSIT_DUE,
        title="Deposit Due",
        description=f"Deposit of R{lease.deposit:,.0f} due",
        date=deposit_date,
    ))

    # 2. Move-in Inspection — 1 day before start (clamped to start)
    inspection_in_date = max(start - timedelta(days=1), start)
    events.append(LeaseEvent(
        lease=lease,
        event_type=E.INSPECTION_IN,
        title="Move-in Inspection",
        description="Conduct move-in / incoming inspection and record property condition",
        date=inspection_in_date,
    ))

    # 3. Contract Start
    events.append(LeaseEvent(
        lease=lease,
        event_type=E.CONTRACT_START,
        title="Lease Start",
        description="Lease agreement commences",
        date=start,
    ))

    # 4. First Rent Due — 1st of month after start
    first_rent = _first_of_next_month(start)
    if first_rent <= end:
        events.append(LeaseEvent(
            lease=lease,
            event_type=E.FIRST_RENT,
            title="First Rent Due",
            description=f"First monthly rent of R{lease.monthly_rent:,.0f} due",
            date=first_rent,
        ))

    # 5. Monthly Rent Due — every month for the lease period (marked recurring)
    rent_cursor = _first_of_next_month(first_rent) if first_rent <= end else None
    while rent_cursor and rent_cursor <= end:
        events.append(LeaseEvent(
            lease=lease,
            event_type=E.RENT_DUE,
            title=f"Rent Due — {rent_cursor.strftime('%b %Y')}",
            description=f"Monthly rent of R{lease.monthly_rent:,.0f} due",
            date=rent_cursor,
            is_recurring=True,
            recurrence_day=1,
        ))
        rent_cursor += relativedelta(months=1)

    # 6. Routine Inspections — every 6 months from start
    routine = start + relativedelta(months=6)
    count = 1
    while routine < end:
        events.append(LeaseEvent(
            lease=lease,
            event_type=E.INSPECTION_ROUTINE,
            title=f"Routine Inspection #{count}",
            description="6-monthly routine property inspection",
            date=routine,
        ))
        routine += relativedelta(months=6)
        count += 1

    # 7. Renewal Review — 60 days before end
    renewal_date = end - timedelta(days=60)
    if renewal_date > start:
        events.append(LeaseEvent(
            lease=lease,
            event_type=E.RENEWAL_REVIEW,
            title="Renewal Review",
            description="Review whether lease will be renewed or terminated",
            date=renewal_date,
        ))

    # 8. Notice Deadline — notice_period_days before end
    notice_date = end - timedelta(days=notice)
    if notice_date > start:
        events.append(LeaseEvent(
            lease=lease,
            event_type=E.NOTICE_DEADLINE,
            title="Notice Period Deadline",
            description=f"Last day to give {notice}-day notice of termination",
            date=notice_date,
        ))

    # 9. Move-out Inspection — on end date
    events.append(LeaseEvent(
        lease=lease,
        event_type=E.INSPECTION_OUT,
        title="Move-out Inspection",
        description="Conduct move-out / outgoing inspection and record property condition",
        date=end,
    ))

    # 10. Contract End
    events.append(LeaseEvent(
        lease=lease,
        event_type=E.CONTRACT_END,
        title="Lease End",
        description="Lease agreement expires",
        date=end,
    ))

    # Bulk create
    LeaseEvent.objects.bulk_create(events)

    # Mark overdue events
    _refresh_statuses(lease)


def _refresh_statuses(lease: Lease) -> None:
    """Update UPCOMING → OVERDUE for past events."""
    today = date.today()
    lease.events.filter(
        status=S.UPCOMING, date__lt=today
    ).update(status=S.OVERDUE)
    lease.events.filter(
        status=S.UPCOMING, date=today
    ).update(status=S.DUE)


def generate_onboarding_steps(lease: Lease) -> None:
    """Create standard onboarding checklist for a new lease. Idempotent."""
    if lease.onboarding_steps.exists():
        return

    ST = OnboardingStep.StepType
    steps = [
        (ST.DEPOSIT_PAYMENT,    "Deposit payment received",         0),
        (ST.LEASE_SIGNED,       "Lease agreement signed by all parties", 1),
        (ST.ID_VERIFIED,        "Tenant ID / CIPC documents verified",   2),
        (ST.MOVE_IN_INSPECTION, "Move-in inspection completed",          3),
        (ST.KEY_HANDOVER,       "Keys handed over to tenant",            4),
        (ST.INVOICING_SETUP,    "Invoicing / debit order set up",        5),
        (ST.TENANT_APP_SETUP,   "Tenant portal / app account created",   6),
        (ST.WELCOME_SENT,       "Welcome message sent to tenant",        7),
    ]
    OnboardingStep.objects.bulk_create([
        OnboardingStep(lease=lease, step_type=st, title=title, order=order)
        for st, title, order in steps
    ])
