"""
Canonical merge field registry for Klikk lease templates.

.. deprecated:: 2026-05
   Source of truth has moved to ``content/legal/merge_fields/``. This
   module is a compatibility shim and will be retired in lease-AI
   Phase 2. New code should use ``apps.leases.merge_fields_loader``
   directly — in particular ``filter_by_context()`` for per-request
   field subsets and ``render_for_drafter_system_block()`` for the
   AI Drafter's cached system block (architecture doc §6.6).

Legacy contract preserved:
    - ``CANONICAL_MERGE_FIELDS`` — ``list[tuple[str, str, str]]`` of
      ``(category, name, label)``. Imported by ``esigning/services.py``,
      ``leases/template_views.py`` (build_merge_fields_prompt_block
      consumer), the field widget, and a handful of regression tests.
    - ``CANONICAL_FIELD_NAMES`` — ``frozenset[str]`` of every field
      name.
    - ``build_merge_fields_prompt_block()`` — string for the legacy AI
      template chat system prompt. The lease-AI v2 Drafter uses
      ``render_for_drafter_system_block(filter_by_context(...))``
      instead.

If YAML loading fails (missing files, schema violation), this module
falls back to a hard-coded minimal safety set (landlord_name,
tenant_name, property_address, lease_start, lease_end, monthly_rent,
deposit) so importers never crash — but a ``CRITICAL`` log line fires
so the failure is visible in alerts.
"""
from __future__ import annotations

import logging
from collections import OrderedDict
from functools import cache

logger = logging.getLogger(__name__)


# ── Safety fallback ──────────────────────────────────────────────────── #


# Minimal set the lease pipeline cannot function without. Used only when
# the YAML loader raises during import. Keeps imports green; the CRITICAL
# log line is the alerting surface.
_FALLBACK_MERGE_FIELDS: list[tuple[str, str, str]] = [
    ("landlord", "landlord_name", "Full name (individual) or trading name (company)"),
    ("property", "property_address", "Full street address of the property"),
    ("tenant", "tenant_name", "Full name of primary tenant"),
    ("lease_terms", "lease_start", "Lease commencement date"),
    ("lease_terms", "lease_end", "Lease expiry / end date"),
    ("lease_terms", "monthly_rent", "Monthly rental amount (numeric)"),
    ("lease_terms", "deposit", "Deposit amount (numeric)"),
]


# ── Lazy load + cache ────────────────────────────────────────────────── #


@cache
def _load_canonical_merge_fields() -> list[tuple[str, str, str]]:
    """Read the YAML catalogue via the loader and return tuple form.

    On any loader failure we log CRITICAL and return the fallback. We
    NEVER re-raise — importers (esigning, AI chat, the field widget,
    Django startup) must keep working.
    """
    try:
        from apps.leases.merge_fields_loader import load_all_fields

        fields = load_all_fields()
    except Exception:
        logger.critical(
            "merge_fields: YAML loader failed; falling back to minimal safety "
            "set (%d fields). Check content/legal/merge_fields/ and "
            "content/legal/_schema/merge_field.schema.json.",
            len(_FALLBACK_MERGE_FIELDS),
            exc_info=True,
        )
        return list(_FALLBACK_MERGE_FIELDS)

    return [(f.category, f.name, f.label) for f in fields]


# Module-level constants — computed lazily on first access.
# We materialise them at import time so the legacy contract holds
# (importers expect a plain list / frozenset).
CANONICAL_MERGE_FIELDS: list[tuple[str, str, str]] = _load_canonical_merge_fields()
"""Legacy tuple-form catalogue of every merge field. Read-only.

Each element is ``(category, name, label)``. Sourced from the YAML
catalogue at ``content/legal/merge_fields/`` via
``apps.leases.merge_fields_loader``.
"""

CANONICAL_FIELD_NAMES: frozenset[str] = frozenset(
    f for _, f, _ in CANONICAL_MERGE_FIELDS
)
"""O(1) lookup set of every canonical field name."""


# ── Category labels for the legacy AI prompt block ──────────────────── #


_CATEGORY_LABELS: dict[str, str] = {
    "landlord": "Landlord",
    "landlord_bank": "Landlord Bank",
    "property": "Property",
    "tenant": "Tenant (primary)",
    "tenant_1": "Tenant 1 (numbered alias for primary)",
    "tenant_2": "Tenant 2",
    "tenant_3": "Tenant 3",
    "co_tenants": "Co-Tenants",
    "occupant_1": "Occupant 1",
    "occupant_2": "Occupant 2",
    "occupant_3": "Occupant 3",
    "occupant_4": "Occupant 4",
    "lease_terms": "Lease Terms",
    "services": "Property Services",
}


def build_merge_fields_prompt_block() -> str:
    """Return the 'Available Merge Fields' section for the legacy AI prompt.

    Groups fields by category in a compact multi-line format (~550 tokens).
    Retained for the v1 lease-template-AI chat endpoint; the v2 Drafter
    uses ``merge_fields_loader.render_for_drafter_system_block()`` instead.
    """
    groups: OrderedDict[str, list[str]] = OrderedDict()
    for cat, field, _ in CANONICAL_MERGE_FIELDS:
        groups.setdefault(cat, []).append(field)

    lines = [
        "## Available Merge Fields",
        "Use {{ field_name }} syntax. All fields below are populated at signing time.",
        "For COMPANY landlords use: landlord_entity_name, landlord_registration_no, "
        "landlord_vat_no, landlord_representative.",
        "For INDIVIDUAL landlords use: landlord_name, landlord_id.",
        "",
        "**Multi-tenant fields are OPT-IN.** Default to a SINGLE tenant (`tenant_name`,"
        " `tenant_id`, `tenant_email`, …) unless the user explicitly says 'co-tenant',"
        " 'second tenant', or names additional tenants. The `tenant_2_*` and `tenant_3_*`"
        " fields exist for households with multiple legal renters — using them when the"
        " user didn't ask creates extra empty signing lines and confuses signers. Same"
        " rule for `occupant_2/3/4` — only add a slot when the user describes a"
        " non-tenant occupant (e.g. a child, partner, or sub-tenant).",
        "",
    ]
    for cat, fields in groups.items():
        label = _CATEGORY_LABELS.get(cat, cat)
        if cat == "tenant_2":
            label = "Tenant 2 (OPT-IN — only when user explicitly names a co-tenant)"
        elif cat == "tenant_3":
            label = "Tenant 3 (OPT-IN — only when user explicitly names a third tenant)"
        elif cat == "occupant_2":
            label = "Occupant 2 (OPT-IN — only when user names a second non-tenant occupant)"
        elif cat == "occupant_3":
            label = "Occupant 3 (OPT-IN — only when user names a third non-tenant occupant)"
        elif cat == "occupant_4":
            label = "Occupant 4 (OPT-IN — only when user names a fourth non-tenant occupant)"
        lines.append(f"{label}: {', '.join(fields)}")

    return "\n".join(lines)
