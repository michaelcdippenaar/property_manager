"""
Cross-entity person and company lookup endpoint.

Searches across User, Person, Landlord, and active leases by:
  - id_number   — SA ID number or passport number (13-digit or passport format)
  - registration_number — Company/Trust/CC registration number (YYYY/XXXXXX/07 or CKxxxx or ITxxxx)

Used by the document classifier skill to detect when a person in an uploaded
document already exists in the system in another capacity (e.g. a director
who is also a tenant, or a company that is already a landlord).
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import User, Person
from .permissions import IsAgentOrAdmin


class EntityLookupView(APIView):
    """
    GET /api/v1/accounts/lookup/?id_number=<id>
    GET /api/v1/accounts/lookup/?registration_number=<reg>

    Returns all system records matching the given identifier across:
      - User accounts (tenants, agents, owners)
      - Person records (lease tenants, co-tenants, guarantors, occupants)
      - Landlords (owners of properties)
    """
    permission_classes = [IsAuthenticated, IsAgentOrAdmin]

    def get(self, request):
        id_number = request.query_params.get("id_number", "").strip()
        registration_number = request.query_params.get("registration_number", "").strip()

        if not id_number and not registration_number:
            return Response(
                {"detail": "Provide id_number or registration_number as a query parameter."},
                status=400,
            )

        results = {
            "query": {
                "id_number": id_number or None,
                "registration_number": registration_number or None,
            },
            "matches": [],
        }

        # ── 1. User accounts (tenants, agents, admins, owners) ──────────────
        if id_number:
            for user in User.objects.filter(id_number=id_number):
                entry = {
                    "source": "User",
                    "id": user.id,
                    "full_name": f"{user.first_name} {user.last_name}".strip(),
                    "email": user.email,
                    "phone": user.phone,
                    "role": user.role,
                    "is_active": user.is_active,
                    "related": [],
                }
                # If the user has a linked Person profile, surface their primary leases
                person_profile = getattr(user, "person_profile", None)
                if person_profile is not None:
                    for lease in person_profile.leases_as_primary.select_related(
                        "unit__property",
                    ).all():
                        entry["related"].append({
                            "type": "Lease (primary tenant)",
                            "lease_id": lease.id,
                            "unit": str(lease.unit),
                            "property": str(lease.unit.property) if lease.unit else None,
                            "status": lease.status,
                        })
                results["matches"].append(entry)

        # ── 2. Person records (lease parties) ───────────────────────────────
        if id_number:
            for person in Person.objects.filter(id_number=id_number).prefetch_related(
                "leases_as_primary__unit__property",
                "co_tenancies__lease__unit__property",
                "guarantees__lease__unit__property",
                "occupancies__lease__unit__property",
            ):
                entry = {
                    "source": "Person",
                    "id": person.id,
                    "full_name": person.full_name,
                    "person_type": person.person_type,
                    "email": person.email,
                    "phone": person.phone,
                    "related": [],
                }
                for lease in person.leases_as_primary.all():
                    entry["related"].append({
                        "type": "Lease (primary tenant)",
                        "lease_id": lease.id,
                        "unit": str(lease.unit),
                        "property": str(lease.unit.property) if lease.unit else None,
                        "status": lease.status,
                    })
                for lt in person.co_tenancies.all():
                    entry["related"].append({
                        "type": "Lease (co-tenant)",
                        "lease_id": lt.lease_id,
                        "unit": str(lt.lease.unit),
                        "status": lt.lease.status,
                    })
                for lg in person.guarantees.all():
                    entry["related"].append({
                        "type": "Lease (guarantor)",
                        "lease_id": lg.lease_id,
                        "unit": str(lg.lease.unit),
                        "status": lg.lease.status,
                    })
                for lo in person.occupancies.all():
                    entry["related"].append({
                        "type": "Lease (occupant)",
                        "lease_id": lo.lease_id,
                        "unit": str(lo.lease.unit),
                        "status": lo.lease.status,
                    })
                results["matches"].append(entry)

        # ── 3. Landlords ─────────────────────────────────────────────────────
        from apps.properties.models import Landlord
        landlord_qs = Landlord.objects.none()
        if id_number:
            landlord_qs = landlord_qs | Landlord.objects.filter(id_number=id_number)
        if registration_number:
            landlord_qs = landlord_qs | Landlord.objects.filter(registration_number=registration_number)

        for landlord in landlord_qs.prefetch_related("ownerships__property"):
            entry = {
                "source": "Landlord",
                "id": landlord.id,
                "full_name": landlord.name,
                "landlord_type": landlord.landlord_type,
                "registration_number": landlord.registration_number,
                "email": landlord.email,
                "phone": landlord.phone,
                "related": [],
            }
            for ownership in landlord.ownerships.all():
                prop = ownership.property
                if prop is None:
                    continue
                entry["related"].append({
                    "type": "Property (landlord)",
                    "property_id": prop.id,
                    "address": str(prop),
                })
            results["matches"].append(entry)

        results["total_matches"] = len(results["matches"])
        return Response(results)
