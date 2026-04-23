"""
RHA compliance checker for Klikk leases.

Checks a Lease instance (and optionally its builder session state) against
RHA s5 requirements and returns a structured flag list.

Flag structure:
    {
        "code":     "DEPOSIT_EXCEEDS_2X",          # machine-readable key
        "section":  "RHA s5(3)(g)",                 # legal citation
        "severity": "blocking" | "advisory",        # blocking halts finalize/send_for_signing
        "message":  "Human-readable explanation",
        "field":    "deposit",                      # field name on Lease model (for CTA routing)
    }

Usage:
    from apps.leases.rha_check import run_rha_checks

    flags = run_rha_checks(lease)
    blocking = [f for f in flags if f["severity"] == "blocking"]
"""
from __future__ import annotations
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Lease


def run_rha_checks(lease: "Lease") -> list[dict]:
    """
    Run all RHA compliance checks against *lease* and return the full flag list.

    Blocking flags prevent finalize / send-for-signing.
    Advisory flags are shown as yellow warnings but do not block.
    """
    flags: list[dict] = []

    _check_mandatory_terms(lease, flags)
    _check_deposit(lease, flags)
    _check_notice_period(lease, flags)
    _check_inspection_events(lease, flags)

    return flags


# ── Individual checkers ────────────────────────────────────────────────── #

def _flag(flags: list, *, code: str, section: str, severity: str, message: str, field: str):
    flags.append({
        "code": code,
        "section": section,
        "severity": severity,
        "message": message,
        "field": field,
    })


def _check_mandatory_terms(lease: "Lease", flags: list):
    """
    RHA s5(3)(a)-(f): lease must identify parties, premises, rent amount,
    escalation provision, duration, renewal terms, and domicilium.
    We enforce what the model captures; full clause text is beyond model scope.
    """
    # Parties
    if not lease.primary_tenant_id:
        _flag(flags,
              code="MISSING_PRIMARY_TENANT",
              section="RHA s5(3)(a)",
              severity="blocking",
              message="No primary tenant is linked to this lease. A lease must identify the lessee.",
              field="primary_tenant")

    # Premises — unit must exist
    if not lease.unit_id:
        _flag(flags,
              code="MISSING_PREMISES",
              section="RHA s5(3)(b)",
              severity="blocking",
              message="No premises (unit) is linked to this lease. A lease must describe the leased property.",
              field="unit")

    # Rent
    if not lease.monthly_rent or lease.monthly_rent <= 0:
        _flag(flags,
              code="MISSING_RENT",
              section="RHA s5(3)(c)",
              severity="blocking",
              message="Monthly rent is zero or not set. A lease must specify the rental amount.",
              field="monthly_rent")

    # Duration
    if not lease.start_date:
        _flag(flags,
              code="MISSING_START_DATE",
              section="RHA s5(3)(d)",
              severity="blocking",
              message="Lease start date is missing. A lease must specify its commencement date.",
              field="start_date")

    if not lease.end_date:
        _flag(flags,
              code="MISSING_END_DATE",
              section="RHA s5(3)(d)",
              severity="blocking",
              message="Lease end date is missing. A lease must specify its duration or termination date.",
              field="end_date")

    if lease.start_date and lease.end_date and lease.end_date <= lease.start_date:
        _flag(flags,
              code="END_BEFORE_START",
              section="RHA s5(3)(d)",
              severity="blocking",
              message="Lease end date must be after the start date.",
              field="end_date")

    # Escalation provision (RHA s5(3)(f))
    if not getattr(lease, "escalation_clause", None):
        _flag(flags,
              code="MISSING_ESCALATION_CLAUSE",
              section="RHA s5(3)(f)",
              severity="blocking",
              message=(
                  "Escalation clause is missing. The lease must specify the basis on which "
                  "rent will be increased (e.g. CPI-linked or fixed percentage) as required "
                  "by RHA s5(3)(f)."
              ),
              field="escalation_clause")

    # Renewal terms (RHA s5(3)(f))
    if not getattr(lease, "renewal_clause", None):
        _flag(flags,
              code="MISSING_RENEWAL_CLAUSE",
              section="RHA s5(3)(f)",
              severity="blocking",
              message=(
                  "Renewal clause is missing. The lease must describe the renewal terms or "
                  "options available at expiry as required by RHA s5(3)(f)."
              ),
              field="renewal_clause")

    # Domicilium address (RHA s5(3))
    if not getattr(lease, "domicilium_address", None):
        _flag(flags,
              code="MISSING_DOMICILIUM",
              section="RHA s5(3)",
              severity="blocking",
              message=(
                  "Domicilium address (domicilium citandi et executandi) is missing. "
                  "The lease must record the tenant's address for formal legal notices."
              ),
              field="domicilium_address")

    # Notice period
    if not lease.notice_period_days or lease.notice_period_days < 1:
        _flag(flags,
              code="MISSING_NOTICE_PERIOD",
              section="RHA s5(3)(e)",
              severity="blocking",
              message="Notice period is not set. A lease must specify the notice period for cancellation.",
              field="notice_period_days")

    # Deposit (advisory if zero — some leases have no deposit, e.g. social housing)
    if lease.deposit is None:
        _flag(flags,
              code="MISSING_DEPOSIT_FIELD",
              section="RHA s5(3)(f)",
              severity="blocking",
              message="Deposit amount field is not set on this lease.",
              field="deposit")


def _check_deposit(lease: "Lease", flags: list):
    """
    RHA s5(3)(g): deposit must not exceed two months' rent.
    RHA s5(3)(h): deposit must be held in an interest-bearing account.

    The interest-bearing account requirement is advisory (we cannot enforce it
    from the data model alone — it is a landlord obligation after execution).
    We flag it as a reminder.
    """
    rent = lease.monthly_rent
    deposit = lease.deposit

    if rent and deposit is not None and Decimal(str(deposit)) > Decimal(str(rent)) * 2:
        _flag(flags,
              code="DEPOSIT_EXCEEDS_2X_RENT",
              section="RHA s5(3)(g)",
              severity="blocking",
              message=(
                  f"Deposit (R{deposit:,.2f}) exceeds two months' rent (R{rent * 2:,.2f}). "
                  "RHA s5(3)(g) caps the deposit at two months' rental."
              ),
              field="deposit")

    # Pro-rata advisory: if start_date is not the 1st, tenant may pay partial first month
    if lease.start_date and lease.start_date.day != 1:
        _flag(flags,
              code="PRO_RATA_FIRST_MONTH",
              section="RHA s5(3)",
              severity="advisory",
              message=(
                  f"Lease starts on the {lease.start_date.day}{_ordinal(lease.start_date.day)} — "
                  "ensure the first month's rent is pro-rated in the lease document."
              ),
              field="start_date")

    # Interest-bearing account reminder
    _flag(flags,
          code="DEPOSIT_INTEREST_BEARING_REMINDER",
          section="RHA s5(3)(h)",
          severity="advisory",
          message=(
              "Confirm that the deposit is held in a separate, interest-bearing account "
              "as required by RHA s5(3)(h). The deposit and accrued interest must be "
              "returned to the tenant within 14 days of lease end."
          ),
          field="deposit")


def _check_notice_period(lease: "Lease", flags: list):
    """
    RHA s5(3)(e): notice period should be at least
    one calendar month (30 days) for fixed-term leases.
    """
    days = lease.notice_period_days
    if days and days < 20:
        _flag(flags,
              code="NOTICE_PERIOD_TOO_SHORT",
              section="RHA s5(3)(e)",
              severity="blocking",
              message=(
                  f"Notice period is {days} days, which is less than the recommended 20 business days. "
                  "Consider setting at least 30 calendar days to align with RHA practice."
              ),
              field="notice_period_days")


def _check_inspection_events(lease: "Lease", flags: list):
    """
    RHA s5(4)+(5): joint inspection is required at commencement and termination.
    We check whether inspection events have been generated for this lease.
    Advisory only — events may be created after lease finalization.
    """
    from .models import LeaseEvent

    event_types = set(
        lease.events.values_list("event_type", flat=True)
    ) if lease.pk else set()

    if LeaseEvent.EventType.INSPECTION_IN not in event_types:
        _flag(flags,
              code="MISSING_INSPECTION_IN_EVENT",
              section="RHA s5(4)",
              severity="advisory",
              message=(
                  "No move-in inspection event has been scheduled. "
                  "RHA s5(4) requires a joint inspection at commencement. "
                  "Generate lease events to create this reminder."
              ),
              field="events")

    if LeaseEvent.EventType.INSPECTION_OUT not in event_types:
        _flag(flags,
              code="MISSING_INSPECTION_OUT_EVENT",
              section="RHA s5(5)",
              severity="advisory",
              message=(
                  "No move-out inspection event has been scheduled. "
                  "RHA s5(5) requires a joint inspection at termination. "
                  "Generate lease events to create this reminder."
              ),
              field="events")


# ── Helpers ────────────────────────────────────────────────────────────── #

def _ordinal(n: int) -> str:
    suffixes = {1: "st", 2: "nd", 3: "rd"}
    return suffixes.get(n % 10, "th") if n % 100 not in (11, 12, 13) else "th"


def blocking_flags(flags: list[dict]) -> list[dict]:
    """Filter *flags* to only the blocking ones."""
    return [f for f in flags if f.get("severity") == "blocking"]


def advisory_flags(flags: list[dict]) -> list[dict]:
    """Filter *flags* to only the advisory (non-blocking) ones."""
    return [f for f in flags if f.get("severity") == "advisory"]
