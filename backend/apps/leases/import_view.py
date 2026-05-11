from datetime import date, datetime
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from apps.accounts.models import Person, User
from apps.accounts.scoping import _is_admin
from apps.properties.models import Property, Unit
from .models import Lease, LeaseTenant, LeaseOccupant, LeaseGuarantor


def _normalize_phone(raw: str) -> str:
    """Strip everything that isn't a digit (or leading +).

    Same human entered as ``"082 306 8144"``, ``"0823068144"`` or
    ``"+27 82 306 8144"`` should collapse to a single normalised key so
    lookups match across UI input quirks. We keep the leading ``+`` (if
    any) but drop everything else.
    """
    if not raw:
        return ""
    raw = raw.strip()
    plus = raw.startswith("+")
    digits = "".join(c for c in raw if c.isdigit())
    return ("+" if plus else "") + digits


def _phone_variants(raw: str) -> list[str]:
    """Return all reasonable lookup keys for a phone number.

    Stored values may be canonical ("0823068144") or contain spaces /
    country prefix. Match on every plausible representation so we never
    fail to find an obvious duplicate just because the format differs
    between an existing record and the new import.

    SA-aware: "+27 82 306 8144", "0823068144", and "082 306 8144" all
    refer to the same number — generate cross-format variants so any
    one of them looks up the others.
    """
    if not raw:
        return []
    raw = raw.strip()
    normalised = _normalize_phone(raw)  # keeps leading + if any
    out: list[str] = []

    def _add(v: str) -> None:
        if v and v not in out:
            out.append(v)

    _add(raw)
    _add(normalised)

    # Without the leading + (some DB rows store bare digits).
    bare = normalised.lstrip("+")
    _add(bare)

    # SA-specific: +27NNNNNNNNN ↔ 0NNNNNNNNN.
    if bare.startswith("27") and len(bare) > 2:
        _add("0" + bare[2:])
        _add("+27" + bare[2:])
    elif bare.startswith("0") and len(bare) > 1:
        _add("+27" + bare[1:])
        _add("27" + bare[1:])

    return out


def _get_or_create_person(data: dict, agency_id) -> tuple[Person, bool]:
    """Find a matching Person by ID number, phone, or email — or create a new one.

    All lookups and the create are scoped to ``agency_id`` so an importer in
    agency A can never silently re-use a Person belonging to agency B.

    Returns ``(person, matched)`` where ``matched=True`` means we reused an
    existing record (caller may want to surface "linked to existing tenant"
    in the response). ``matched=False`` means a fresh row was created.
    """
    id_number = (data.get("id_number") or "").strip()
    full_name = (data.get("full_name") or "").strip()
    phone = (data.get("phone") or "").strip()
    email = (data.get("email") or "").strip().lower()
    country = (data.get("country") or "").strip()
    phone_country_code = (data.get("phone_country_code") or "").strip()

    if not full_name:
        return None, False

    base_qs = Person.objects.filter(agency_id=agency_id)

    # Match on SA ID number (most reliable)
    if id_number:
        person = base_qs.filter(id_number=id_number).first()
        if person:
            return person, True

    # Match on phone — try all normalised variants so "082 306 8144" and
    # "0823068144" match the same DB row.
    variants = _phone_variants(phone)
    if variants:
        person = base_qs.filter(phone__in=variants).first()
        if person:
            return person, True

    # Match on email (case-insensitive)
    if email:
        person = base_qs.filter(email__iexact=email).first()
        if person:
            return person, True

    # Store phone in normalised form so future lookups don't depend on input formatting.
    create_kwargs = dict(
        agency_id=agency_id,
        full_name=full_name,
        id_number=id_number or "",
        phone=_normalize_phone(phone),
        email=email,
        person_type="individual",
    )
    # Only override the model defaults when the caller actually supplied a value —
    # otherwise the Person model defaults (ZA / +27) apply.
    if country:
        create_kwargs["country"] = country
    if phone_country_code:
        create_kwargs["phone_country_code"] = phone_country_code
    return Person.objects.create(**create_kwargs), False


class ImportLeaseView(APIView):
    """
    Atomic lease import. Accepts fully-reviewed parsed data from the frontend
    and creates: Property (opt) → Unit (opt) → Persons → Lease → Parties.
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        d = request.data

        # Phase 2.4 — resolve the caller's agency_id for stamping new
        # Property / Unit / Lease records. Non-admin users without an
        # agency cannot create leases.
        caller_agency_id = getattr(request.user, "agency_id", None)
        if caller_agency_id is None and not _is_admin(request.user):
            return Response(
                {"error": "Your user account is not linked to an agency."},
                status=400,
            )

        # Scoped Property lookup so cross-tenant property_id values 404.
        property_qs = Property.objects.all()
        if not _is_admin(request.user):
            property_qs = property_qs.filter(agency_id=caller_agency_id)

        # ── Property ───────────────────────────────────────────────────────
        property_id = d.get("property_id")
        if property_id:
            try:
                prop = property_qs.get(pk=property_id)
            except Property.DoesNotExist:
                return Response({"error": "Property not found."}, status=400)
        else:
            prop_data = d.get("property") or {}
            if not prop_data.get("name"):
                return Response({"error": "property.name is required when creating a new property."}, status=400)
            managing_agent = None
            if request.user.role == User.Role.AGENT:
                managing_agent = request.user
            elif request.user.role == User.Role.ADMIN:
                raw = d.get("managing_agent_id") if d.get("managing_agent_id") is not None else d.get("agent_id")
                if raw is not None and raw != "":
                    try:
                        aid = int(raw)
                    except (TypeError, ValueError):
                        aid = None
                    if aid:
                        managing_agent = User.objects.filter(pk=aid, role=User.Role.AGENT).first()
            # Re-use existing property — match by ERF number first, then address
            prop = None
            erf = (prop_data.get("erf_number") or "").strip()
            if erf:
                from apps.properties.models import PropertyDetail
                detail_qs = PropertyDetail.objects.filter(erf_number__iexact=erf).select_related("property")
                if not _is_admin(request.user):
                    detail_qs = detail_qs.filter(property__agency_id=caller_agency_id)
                detail = detail_qs.first()
                if detail:
                    prop = detail.property
            if not prop:
                addr = (prop_data.get("address") or "").strip()
                if addr:
                    prop = property_qs.filter(address__iexact=addr).first()
            if not prop:
                prop = Property.objects.create(
                    agency_id=caller_agency_id,
                    name=prop_data["name"],
                    property_type=prop_data.get("property_type", "house"),
                    address=prop_data.get("address", ""),
                    city=prop_data.get("city", ""),
                    province=prop_data.get("province", ""),
                    postal_code=prop_data.get("postal_code", ""),
                    description=prop_data.get("description", ""),
                    agent=managing_agent,
                )

        # ── Unit ────────────────────────────────────────────────────────────
        unit_id = d.get("unit_id")
        if unit_id:
            try:
                unit = Unit.objects.get(pk=unit_id, property=prop)
            except Unit.DoesNotExist:
                return Response({"error": "Unit not found on that property."}, status=400)
        else:
            unit_data = d.get("unit") or {}
            unit_number = unit_data.get("unit_number", "1")
            unit = Unit.objects.filter(property=prop, unit_number=unit_number).first()
            if not unit:
                unit = Unit.objects.create(
                    agency_id=prop.agency_id,
                    property=prop,
                    unit_number=unit_number,
                    bedrooms=unit_data.get("bedrooms", 1),
                    bathrooms=unit_data.get("bathrooms", 1),
                    rent_amount=d.get("monthly_rent") or unit_data.get("rent_amount", 0),
                )

        # ── Primary Tenant ──────────────────────────────────────────────────
        # Persons are agency-scoped — use the property's agency (which the
        # caller already passed scoping for) so all parties end up under the
        # same tenancy as the lease.
        person_agency_id = prop.agency_id
        primary_data = d.get("primary_tenant") or {}
        primary_person, primary_matched = _get_or_create_person(primary_data, agency_id=person_agency_id)
        if not primary_person:
            return Response({"error": "primary_tenant.full_name is required."}, status=400)

        # Track which Persons we linked vs created so the response can show
        # "Linked to existing tenant Joe Smith (already on Property X)" toasts.
        matched_persons: list[dict] = []
        if primary_matched:
            matched_persons.append({"role": "primary_tenant", "id": primary_person.id, "full_name": primary_person.full_name})

        # ── Validate required date fields ───────────────────────────────────
        start_date = (d.get("start_date") or "").strip() or None
        end_date   = (d.get("end_date")   or "").strip() or None
        if not start_date:
            return Response({"error": "start_date is required."}, status=400)
        if not end_date:
            return Response({"error": "end_date is required."}, status=400)

        # Validate dates are real calendar dates (e.g. reject 2025-11-31)
        for label, val in [("start_date", start_date), ("end_date", end_date)]:
            try:
                datetime.strptime(val, "%Y-%m-%d")
            except ValueError:
                return Response(
                    {"error": f"{label} '{val}' is not a valid date. Please correct it."},
                    status=400,
                )

        # ── Lease ────────────────────────────────────────────────────────────
        lease_fields = {
            "agency_id": prop.agency_id,
            "unit": unit,
            "primary_tenant": primary_person,
            "start_date": start_date,
            "end_date": end_date,
            "monthly_rent": d.get("monthly_rent") or 0,
            "deposit": d.get("deposit") or 0,
            "status": d.get("status", "pending"),
            "lease_number": (d.get("lease_number") or "").strip(),
            "max_occupants": d.get("max_occupants", 1),
            "water_included": d.get("water_included", True),
            "water_limit_litres": d.get("water_limit_litres", 4000),
            "electricity_prepaid": d.get("electricity_prepaid", True),
            # Per-lease service overrides (also defaulted from the property by the
            # ``inherit_services_from_property`` pre_save signal on first save).
            # When the caller passes a value we honour it; otherwise we omit the
            # key so the signal can fill it in from Property defaults.
            **{k: d[k] for k in (
                "water_arrangement",
                "electricity_arrangement",
                "gardening_service_included",
                "wifi_included",
                "security_service_included",
            ) if k in d and d[k] not in (None, "")},
            "notice_period_days": d.get("notice_period_days", 20),
            "early_termination_penalty_months": d.get("early_termination_penalty_months", 3),
            "payment_reference": d.get("payment_reference", ""),
            "ai_parse_result": d.get("ai_parse_result"),
        }
        lease = Lease.objects.create(**lease_fields)

        # Auto-generate lease number if none was provided or found in the document
        if not lease.lease_number:
            lease.lease_number = f"L-{date.today().strftime('%Y%m')}-{lease.id:04d}"
            lease.save(update_fields=["lease_number"])

        # ── Co-tenants ───────────────────────────────────────────────────────
        for ct_data in (d.get("co_tenants") or []):
            person, matched = _get_or_create_person(ct_data, agency_id=person_agency_id)
            if person:
                if matched:
                    matched_persons.append({"role": "co_tenant", "id": person.id, "full_name": person.full_name})
                LeaseTenant.objects.get_or_create(
                    lease=lease, person=person,
                    defaults={
                        "agency_id": lease.agency_id,
                        "payment_reference": (ct_data.get("payment_reference") or "") if isinstance(ct_data, dict) else "",
                    },
                )

        # ── Occupants ────────────────────────────────────────────────────────
        for oc_data in (d.get("occupants") or []):
            person, matched = _get_or_create_person(oc_data, agency_id=person_agency_id)
            if person:
                if matched:
                    matched_persons.append({"role": "occupant", "id": person.id, "full_name": person.full_name})
                LeaseOccupant.objects.get_or_create(
                    lease=lease, person=person,
                    defaults={
                        "agency_id": lease.agency_id,
                        "relationship_to_tenant": oc_data.get("relationship_to_tenant", ""),
                    },
                )

        # ── Guarantors ───────────────────────────────────────────────────────
        for g_data in (d.get("guarantors") or []):
            person, matched = _get_or_create_person(g_data, agency_id=person_agency_id)
            if person:
                if matched:
                    matched_persons.append({"role": "guarantor", "id": person.id, "full_name": person.full_name})
                # Resolve who they cover by name — scoped so we don't bind the
                # guarantor to a same-named Person in another agency.
                covers_name = (g_data.get("for_tenant") or "").strip()
                covers = None
                if covers_name:
                    covers = Person.objects.filter(
                        agency_id=person_agency_id,
                        full_name__iexact=covers_name,
                    ).first()
                LeaseGuarantor.objects.create(
                    agency_id=lease.agency_id, lease=lease,
                    person=person, covers_tenant=covers,
                )

        return Response({
            "id": lease.id,
            "status": lease.status,
            "lease_number": lease.lease_number,
            "primary_tenant_id": primary_person.id,
            "co_tenant_person_ids": list(lease.co_tenants.values_list("person_id", flat=True)),
            "guarantor_person_ids": list(lease.guarantors.values_list("person_id", flat=True)),
            # Frontend uses this to show "Linked to existing tenant <name>"
            # toasts so the user understands that no new Person was created
            # for parties that matched an existing record by phone / id_number
            # / email within the same agency.
            "matched_persons": matched_persons,
        }, status=status.HTTP_201_CREATED)
