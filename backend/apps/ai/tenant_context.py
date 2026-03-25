"""
Build tenant-specific structured context for the AI system prompt.

Pulls data from the database (Lease, Unit, Property, UnitInfo, PropertyAgentConfig,
co-tenants/occupants) so the bot can answer personal questions like "when does my
lease end?" or "what's the WiFi password?" without relying solely on RAG.
"""

from __future__ import annotations

import logging

from django.db.models import Q

from apps.leases.models import Lease, LeaseTenant, LeaseOccupant
from apps.properties.models import Property, PropertyAgentConfig, Unit, UnitInfo

logger = logging.getLogger(__name__)


def _safe_unit_info(unit: Unit, prop: Property) -> list[tuple[str, str]]:
    """Return (label, value) pairs from UnitInfo, using raw SQL to handle schema drift."""
    from django.db import connection, transaction

    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT label, value FROM properties_unitinfo "
                    "WHERE (unit_id = %s OR unit_id IS NULL) "
                    "AND (superseded_at IS NULL) "
                    'ORDER BY coalesce("order", 0), label',
                    [unit.pk],
                )
                return [(r[0], r[1]) for r in cursor.fetchall()]
    except Exception:
        return []


def build_tenant_context(user) -> str:
    """
    Assemble a structured text block with everything we know about this tenant's
    tenancy, property, and unit.  Injected into the Claude system prompt alongside
    RAG excerpts.

    Returns an empty string if no active lease is found.
    """
    lease = (
        Lease.objects.filter(
            Q(primary_tenant__linked_user=user)
            | Q(co_tenants__person__linked_user=user)
            | Q(occupants__person__linked_user=user),
            status=Lease.Status.ACTIVE,
        )
        .select_related("unit__property", "primary_tenant")
        .order_by("-start_date")
        .first()
    )
    if not lease:
        return ""

    unit: Unit = lease.unit
    prop: Property = unit.property
    sections: list[str] = []

    # ── Tenant identity ──
    name = ""
    if lease.primary_tenant:
        name = lease.primary_tenant.full_name or ""
    if not name:
        name = f"{user.first_name} {user.last_name}".strip() or user.email
    sections.append(f"Tenant name: {name}")

    # ── Property & unit ──
    address_parts = [prop.address, prop.city, prop.province, prop.postal_code]
    address = ", ".join(p for p in address_parts if p and p.strip())
    sections.append(f"Property: {prop.name}")
    sections.append(f"Address: {address}")
    sections.append(f"Unit: {unit.unit_number}")
    sections.append(f"Unit type: {prop.get_property_type_display()}")
    sections.append(f"Bedrooms: {unit.bedrooms}, Bathrooms: {unit.bathrooms}")

    # ── Lease terms ──
    sections.append(f"Lease start: {lease.start_date}")
    sections.append(f"Lease end: {lease.end_date}")
    sections.append(f"Monthly rent: R{lease.monthly_rent:,.2f}")
    sections.append(f"Deposit: R{lease.deposit:,.2f}")
    sections.append(f"Max occupants: {lease.max_occupants}")
    sections.append(f"Notice period: {lease.notice_period_days} days")
    sections.append(f"Early termination penalty: {lease.early_termination_penalty_months} month(s) rent")

    # ── Utilities ──
    water = "included" if lease.water_included else "tenant pays"
    if lease.water_included and lease.water_limit_litres:
        water += f" (limit: {lease.water_limit_litres:,} litres/month)"
    elec = "prepaid meter" if lease.electricity_prepaid else "post-paid / included"
    sections.append(f"Water: {water}")
    sections.append(f"Electricity: {elec}")

    # ── Co-tenants / occupants ──
    try:
        co_tenants = LeaseTenant.objects.filter(lease=lease).select_related("person")
        if co_tenants.exists():
            names = [ct.person.full_name for ct in co_tenants if ct.person]
            sections.append(f"Co-tenants: {', '.join(names)}")
    except Exception:
        pass

    try:
        occupants = LeaseOccupant.objects.filter(lease=lease).select_related("person")
        if occupants.exists():
            names = [o.person.full_name for o in occupants if o.person]
            sections.append(f"Occupants: {', '.join(names)}")
    except Exception:
        pass

    # ── UnitInfo key-value pairs (WiFi password, meter number, etc.) ──
    info_pairs = _safe_unit_info(unit, prop)
    if info_pairs:
        sections.append("")
        sections.append("Property/unit information:")
        for label, value in info_pairs:
            sections.append(f"  {label}: {value}")

    # ── PropertyAgentConfig notes ──
    try:
        config = PropertyAgentConfig.objects.filter(property=prop, is_active=True).first()
        if config:
            if config.ai_notes and config.ai_notes.strip():
                sections.append("")
                sections.append(f"Agent notes for this property: {config.ai_notes.strip()}")
            if config.maintenance_playbook and config.maintenance_playbook.strip():
                sections.append(f"Maintenance playbook: {config.maintenance_playbook.strip()}")
    except Exception:
        pass

    if not sections:
        return ""

    header = "--- TENANT & PROPERTY CONTEXT (from database) ---"
    return f"{header}\n" + "\n".join(sections)
