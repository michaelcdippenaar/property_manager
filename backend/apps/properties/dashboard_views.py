"""Portfolio rollup endpoint for the lifecycle dashboard.

Returns one entry per accessible property with the active lease (if any),
the top 3 open/in-progress maintenance jobs (priority-ranked then oldest-first),
and simple unit occupancy counts. Used by `DashboardView.vue`.
"""
from datetime import timedelta

from django.db.models import Case, IntegerField, Value, When
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.leases.models import Lease
from apps.maintenance.models import MaintenanceRequest
from apps.properties.access import get_accessible_property_ids
from apps.properties.models import Property, Unit


_PRIORITY_RANK = Case(
    When(priority=MaintenanceRequest.Priority.URGENT, then=Value(0)),
    When(priority=MaintenanceRequest.Priority.HIGH, then=Value(1)),
    When(priority=MaintenanceRequest.Priority.MEDIUM, then=Value(2)),
    When(priority=MaintenanceRequest.Priority.LOW, then=Value(3)),
    default=Value(4),
    output_field=IntegerField(),
)


def _tenant_names(lease):
    names = []
    if lease.primary_tenant_id and lease.primary_tenant:
        names.append(lease.primary_tenant.full_name)
    for ct in lease.co_tenants.all():
        if ct.person and ct.person.full_name:
            names.append(ct.person.full_name)
    return names


def _serialize_active_lease(lease, today):
    if not lease:
        return None
    successor = lease.successor_lease.first()
    notice_period_days = lease.notice_period_days or 0
    notice_window_date = (
        lease.end_date - timedelta(days=notice_period_days)
        if lease.end_date else None
    )
    names = _tenant_names(lease)
    return {
        "id": lease.id,
        "lease_number": lease.lease_number,
        "status": lease.status,
        "start_date": lease.start_date,
        "end_date": lease.end_date,
        "signed_at": lease.created_at,
        "monthly_rent": str(lease.monthly_rent) if lease.monthly_rent is not None else None,
        "deposit": str(lease.deposit) if lease.deposit is not None else None,
        "notice_period_days": notice_period_days,
        "notice_window_date": notice_window_date,
        "tenant_name": names[0] if names else "",
        "all_tenant_names": names,
        "successor_lease_id": successor.id if successor else None,
    }


def _serialize_maintenance(mr, today):
    created_date = mr.created_at.date() if mr.created_at else today
    return {
        "id": mr.id,
        "title": mr.title,
        "priority": mr.priority,
        "status": mr.status,
        "created_at": mr.created_at,
        "days_open": (today - created_date).days,
    }


class DashboardPortfolioView(APIView):
    """GET /api/v1/dashboard/portfolio/ — per-property lifecycle rollup."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.localdate()
        prop_ids = list(get_accessible_property_ids(request.user))

        properties = (
            Property.objects.filter(pk__in=prop_ids)
            .order_by("name")
        )

        # All active leases within scope, prefetched to avoid N+1
        active_leases_qs = (
            Lease.objects.filter(
                status=Lease.Status.ACTIVE,
                unit__property_id__in=prop_ids,
                start_date__lte=today,
                end_date__gte=today,
            )
            .select_related("unit", "unit__property", "primary_tenant")
            .prefetch_related("co_tenants__person", "successor_lease")
        )
        active_by_property = {}
        for lease in active_leases_qs:
            # If a property has multiple active leases (different units), pick
            # the one ending soonest — that's the most actionable for the landlord.
            cur = active_by_property.get(lease.unit.property_id)
            if cur is None or (lease.end_date and (cur.end_date is None or lease.end_date < cur.end_date)):
                active_by_property[lease.unit.property_id] = lease

        # Units per property, for occupancy
        unit_counts = {}
        for u in Unit.objects.filter(property_id__in=prop_ids).values("property_id", "status"):
            entry = unit_counts.setdefault(u["property_id"], {"total": 0, "occupied": 0})
            entry["total"] += 1
            if u["status"] == Unit.Status.OCCUPIED:
                entry["occupied"] += 1

        # Maintenance — open/in-progress, ranked
        mr_qs = (
            MaintenanceRequest.objects.filter(
                unit__property_id__in=prop_ids,
                status__in=[MaintenanceRequest.Status.OPEN, MaintenanceRequest.Status.IN_PROGRESS],
            )
            .annotate(priority_rank=_PRIORITY_RANK)
            .order_by("priority_rank", "created_at")
            .select_related("unit")
        )
        mr_by_property = {}
        counts_by_property = {}
        for mr in mr_qs:
            pid = mr.unit.property_id
            counts_by_property[pid] = counts_by_property.get(pid, 0) + 1
            bucket = mr_by_property.setdefault(pid, [])
            if len(bucket) < 3:
                bucket.append(mr)

        payload = []
        for prop in properties:
            counts = unit_counts.get(prop.id, {"total": 0, "occupied": 0})
            # Properties with no Unit rows still count as 1 implicit unit.
            if counts["total"] == 0:
                counts = {"total": 1, "occupied": 1 if active_by_property.get(prop.id) else 0}
            payload.append({
                "property_id": prop.id,
                "property_name": prop.name,
                "property_address": prop.address,
                "property_type": prop.property_type,
                "units_total": counts["total"],
                "units_occupied": counts["occupied"],
                "active_lease": _serialize_active_lease(active_by_property.get(prop.id), today),
                "top_maintenance": [
                    _serialize_maintenance(mr, today)
                    for mr in mr_by_property.get(prop.id, [])
                ],
                "open_maintenance_count": counts_by_property.get(prop.id, 0),
            })

        return Response(payload)
