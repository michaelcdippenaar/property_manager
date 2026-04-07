"""
Mandate Services
================
Utilities for generating the rental mandate HTML document and building the
signer list for the native e-signing flow.

Mirrors the pattern in apps/esigning/services.py (build_lease_context /
generate_lease_html) but scoped to RentalMandate objects.
"""
import hashlib
import os
import re

from django.template.loader import render_to_string


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_date(d) -> str:
    if not d:
        return "—"
    try:
        return d.strftime("%-d %B %Y")
    except Exception:
        return str(d)


def _fmt_address(addr: dict) -> str:
    if not addr:
        return "—"
    parts = [
        addr.get("street", ""),
        addr.get("city", ""),
        addr.get("province", ""),
        addr.get("postal_code", ""),
    ]
    return ", ".join(p for p in parts if p) or "—"


def _mandate_duration_text(start_date, end_date) -> str:
    if not end_date:
        return "an indefinite period (month-to-month)"
    try:
        from dateutil.relativedelta import relativedelta
        delta = relativedelta(end_date, start_date)
        months = delta.years * 12 + delta.months
        if months == 12:
            return "12 (twelve) months"
        if months > 0:
            return f"{months} months"
    except Exception:
        pass
    return f"until {_fmt_date(end_date)}"


# ---------------------------------------------------------------------------
# Context builder
# ---------------------------------------------------------------------------

def build_mandate_context(mandate) -> dict:
    """
    Build the merge-field dict for the rental mandate HTML template.
    All values are plain strings — ready for regex substitution.
    """
    from .models import RentalMandate

    ll = mandate.landlord

    # Owner fields (prefer representative if company/trust)
    if ll:
        owner_full_name     = ll.representative_name or ll.name or "—"
        owner_id_reg_number = ll.representative_id_number or ll.id_number or ll.registration_number or "—"
        owner_email_address = ll.representative_email or ll.email or "—"
        owner_contact_number = ll.representative_phone or ll.phone or "—"
        owner_address       = _fmt_address(ll.address)
    else:
        # Fallback: try current PropertyOwnership
        ownership = mandate.property.ownerships.filter(is_current=True).first()
        if ownership:
            owner_full_name      = ownership.representative_name or ownership.owner_name or "—"
            owner_id_reg_number  = ownership.representative_id_number or ownership.registration_number or "—"
            owner_email_address  = ownership.representative_email or ownership.owner_email or "—"
            owner_contact_number = ownership.representative_phone or ownership.owner_phone or "—"
            owner_address        = _fmt_address(ownership.owner_address)
        else:
            owner_full_name = owner_id_reg_number = owner_email_address = owner_contact_number = owner_address = "—"

    # Agency details (from singleton Agency record)
    from apps.accounts.models import Agency
    agency = Agency.get_solo()
    agency_name                = (agency.name if agency else None) or "—"
    agency_registration_number = (agency.registration_number if agency else None) or "—"
    agency_ffc_number          = (agency.eaab_ffc_number if agency else None) or "—"
    agency_contact_number      = (agency.contact_number if agency else None) or "—"
    agency_email_address       = (agency.email if agency else None) or "—"
    agency_physical_address    = (agency.physical_address if agency else None) or "—"

    # Property fields
    prop = mandate.property
    property_address = ", ".join(filter(None, [
        prop.address, prop.city, prop.province, prop.postal_code
    ])) or "—"

    erf_number          = "—"
    unit_number         = "—"
    scheme_name         = "—"
    property_description = prop.description or "—"
    monthly_rental_amount = "—"

    try:
        detail = prop.detail
        erf_number = getattr(detail, "erf_number", None) or "—"
    except Exception:
        pass

    # Try to pick up unit number from a single unit
    units = list(prop.units.all()[:2])
    if len(units) == 1:
        unit_number = units[0].unit_number or "—"
        try:
            monthly_rental_amount = f"{units[0].rent_amount:,.2f}" if units[0].rent_amount else "—"
        except Exception:
            pass

    # Mandate type checkboxes — active type gets ☑, others get ☐
    type_map = {
        "full_management": "full_management",
        "letting_only":    "letting_only",
        "rent_collection": "rent_collection",
        "finders_fee":     "finders_fee",
    }
    mt = mandate.mandate_type
    mandate_type_full_management_check  = "☑" if mt == "full_management"  else "☐"
    mandate_type_letting_only_check     = "☑" if mt == "letting_only"     else "☐"
    mandate_type_rent_collection_check  = "☑" if mt == "rent_collection"  else "☐"
    mandate_type_finders_fee_check      = "☑" if mt == "finders_fee"      else "☐"

    mandate_type_full_management_class  = "active-type" if mt == "full_management"  else "inactive-type"
    mandate_type_letting_only_class     = "active-type" if mt == "letting_only"     else "inactive-type"
    mandate_type_rent_collection_class  = "active-type" if mt == "rent_collection"  else "inactive-type"
    mandate_type_finders_fee_class      = "active-type" if mt == "finders_fee"      else "inactive-type"

    # Exclusivity checkboxes
    ex = mandate.exclusivity
    exclusivity_sole_check  = "☑" if ex == "sole" else "☐"
    exclusivity_open_check  = "☑" if ex == "open" else "☐"
    exclusivity_sole_class  = "active-type" if ex == "sole" else "inactive-type"
    exclusivity_open_class  = "active-type" if ex == "open" else "inactive-type"

    # Commission display
    rate = mandate.commission_rate
    if mandate.commission_period == "once_off":
        commission_rate_display = f"{rate:g} month{'s' if rate != 1 else ''}'s gross rental (excl. VAT)"
    else:
        commission_rate_display = f"{rate:g}% of the gross monthly rental (excl. VAT)"

    # Trust account & financial cycle (from Agency record)
    trust_account_number = (agency.trust_account_number if agency else None) or "—"
    trust_bank_name      = (agency.trust_bank_name if agency else None) or "—"
    statement_date       = (agency.statement_date if agency else None) or "the 5th"
    disbursement_date    = (agency.disbursement_date if agency else None) or "the 7th"
    information_officer_email = (agency.information_officer_email if agency else None) or agency_email_address

    return {
        # Owner
        "owner_full_name":       owner_full_name,
        "owner_id_reg_number":   owner_id_reg_number,
        "owner_email_address":   owner_email_address,
        "owner_contact_number":  owner_contact_number,
        "owner_address":         owner_address,
        # Agency
        "agency_name":                agency_name,
        "agency_registration_number": agency_registration_number,
        "agency_ffc_number":          agency_ffc_number,
        "agency_contact_number":      agency_contact_number,
        "agency_email_address":       agency_email_address,
        "agency_physical_address":    agency_physical_address,
        # Property
        "property_address":       property_address,
        "erf_number":             erf_number,
        "unit_number":            unit_number,
        "scheme_name":            scheme_name,
        "property_description":   property_description,
        "monthly_rental_amount":  monthly_rental_amount,
        # Mandate type checkboxes
        "mandate_type_full_management_check":  mandate_type_full_management_check,
        "mandate_type_letting_only_check":     mandate_type_letting_only_check,
        "mandate_type_rent_collection_check":  mandate_type_rent_collection_check,
        "mandate_type_finders_fee_check":      mandate_type_finders_fee_check,
        "mandate_type_full_management_class":  mandate_type_full_management_class,
        "mandate_type_letting_only_class":     mandate_type_letting_only_class,
        "mandate_type_rent_collection_class":  mandate_type_rent_collection_class,
        "mandate_type_finders_fee_class":      mandate_type_finders_fee_class,
        # Exclusivity
        "exclusivity_sole_check": exclusivity_sole_check,
        "exclusivity_open_check": exclusivity_open_check,
        "exclusivity_sole_class": exclusivity_sole_class,
        "exclusivity_open_class": exclusivity_open_class,
        # Mandate terms
        "commencement_date":       _fmt_date(mandate.start_date),
        "mandate_duration":        _mandate_duration_text(mandate.start_date, mandate.end_date),
        "notice_period":           str(mandate.notice_period_days),
        "maintenance_threshold":   f"{mandate.maintenance_threshold:,.2f}",
        "commission_rate_display": commission_rate_display,
        # Financial / trust
        "trust_account_number":       trust_account_number,
        "trust_bank_name":            trust_bank_name,
        "statement_date":             statement_date,
        "disbursement_date":          disbursement_date,
        "information_officer_email":  information_officer_email,
        # Agent (populated by send_for_signing action with request.user)
        "agent_name": "—",
    }


# ---------------------------------------------------------------------------
# HTML generator
# ---------------------------------------------------------------------------

def generate_mandate_html(mandate, agent_user=None) -> str:
    """
    Render the rental mandate HTML template with merge fields substituted.
    Uses regex mustache substitution (same pattern as generate_lease_html)
    so that custom HTML elements like <signature-field> are not mangled.
    """
    template_path = os.path.join(
        os.path.dirname(__file__), "templates", "mandates", "rental_mandate.html"
    )
    with open(template_path, encoding="utf-8") as fh:
        html = fh.read()

    ctx = build_mandate_context(mandate)

    # Populate agent name from user if provided
    if agent_user:
        full_name = (
            getattr(agent_user, "get_full_name", lambda: "")() or
            getattr(agent_user, "full_name", None) or
            getattr(agent_user, "email", "—")
        )
        ctx["agent_name"] = full_name or "—"

    def _replacer(match):
        key = match.group(1)
        return str(ctx.get(key, f"[{key}]"))

    return re.sub(r"\{\{(\w+)\}\}", _replacer, html)


# ---------------------------------------------------------------------------
# Signer builder
# ---------------------------------------------------------------------------

def build_mandate_signers(mandate, agent_user) -> list:
    """
    Build the two-signer list for the mandate e-signing flow:
      0 — owner / representative (signs first)
      1 — agent (signs after owner completes)
    """
    ll = mandate.landlord

    if ll:
        owner_name  = ll.representative_name or ll.name or "Property Owner"
        owner_email = ll.representative_email or ll.email or ""
        owner_phone = ll.representative_phone or ll.phone or ""
    else:
        ownership = mandate.property.ownerships.filter(is_current=True).first()
        if ownership:
            owner_name  = ownership.representative_name or ownership.owner_name or "Property Owner"
            owner_email = ownership.representative_email or ownership.owner_email or ""
            owner_phone = ownership.representative_phone or ownership.owner_phone or ""
        else:
            owner_name = "Property Owner"
            owner_email = ""
            owner_phone = ""

    agent_name  = (
        getattr(agent_user, "get_full_name", lambda: "")() or
        getattr(agent_user, "full_name", None) or
        agent_user.email
    )
    agent_email = agent_user.email or ""

    return [
        {
            "order":      0,
            "role":       "owner",
            "name":       owner_name,
            "email":      owner_email,
            "phone":      owner_phone,
            "send_email": bool(owner_email),
        },
        {
            "order":      1,
            "role":       "agent",
            "name":       agent_name,
            "email":      agent_email,
            "phone":      "",
            "send_email": bool(agent_email),
        },
    ]
