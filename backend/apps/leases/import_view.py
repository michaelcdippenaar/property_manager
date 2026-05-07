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


def _get_or_create_person(data: dict) -> Person:
    """Find a matching Person by ID number, phone, or email — or create a new one."""
    id_number = (data.get("id_number") or "").strip()
    full_name = (data.get("full_name") or "").strip()
    phone = (data.get("phone") or "").strip()
    email = (data.get("email") or "").strip()

    if not full_name:
        return None

    # Match on SA ID number (most reliable)
    if id_number:
        person = Person.objects.filter(id_number=id_number).first()
        if person:
            return person

    # Match on phone (unique when set)
    if phone:
        person = Person.objects.filter(phone=phone).first()
        if person:
            return person

    # Match on email
    if email:
        person = Person.objects.filter(email=email).first()
        if person:
            return person

    return Person.objects.create(
        full_name=full_name,
        id_number=id_number or "",
        phone=phone,
        email=email,
        person_type="individual",
    )


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
        primary_data = d.get("primary_tenant") or {}
        primary_person = _get_or_create_person(primary_data)
        if not primary_person:
            return Response({"error": "primary_tenant.full_name is required."}, status=400)

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
            person = _get_or_create_person(ct_data)
            if person:
                LeaseTenant.objects.get_or_create(
                    lease=lease, person=person,
                    defaults={"agency_id": lease.agency_id},
                )

        # ── Occupants ────────────────────────────────────────────────────────
        for oc_data in (d.get("occupants") or []):
            person = _get_or_create_person(oc_data)
            if person:
                LeaseOccupant.objects.get_or_create(
                    lease=lease, person=person,
                    defaults={
                        "agency_id": lease.agency_id,
                        "relationship_to_tenant": oc_data.get("relationship_to_tenant", ""),
                    },
                )

        # ── Guarantors ───────────────────────────────────────────────────────
        for g_data in (d.get("guarantors") or []):
            person = _get_or_create_person(g_data)
            if person:
                # Resolve who they cover by name
                covers_name = (g_data.get("for_tenant") or "").strip()
                covers = None
                if covers_name:
                    covers = Person.objects.filter(full_name__iexact=covers_name).first()
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
        }, status=status.HTTP_201_CREATED)
