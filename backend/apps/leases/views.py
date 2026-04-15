from datetime import timedelta
from django.db import transaction
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import Person, User
from .models import Lease, LeaseDocument, LeaseEvent, LeaseTenant, LeaseOccupant, LeaseGuarantor, OnboardingStep, InventoryItem, InventoryTemplate
from .serializers import (
    LeaseSerializer, LeaseDocumentSerializer, LeaseEventSerializer,
    LeaseOccupantSerializer, LeaseGuarantorSerializer, OnboardingStepSerializer, PersonSerializer,
    InventoryItemSerializer, InventoryTemplateSerializer,
)
from .events import generate_lease_events, generate_onboarding_steps


class LeaseViewSet(viewsets.ModelViewSet):
    serializer_class = LeaseSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["status", "unit", "primary_tenant"]

    def perform_destroy(self, instance):
        for doc in instance.documents.all():
            try:
                doc.file.delete(save=False)
            except Exception:
                pass
        instance.delete()

    def get_queryset(self):
        user = self.request.user
        qs = Lease.objects.select_related(
            "unit__property", "unit__property__agent", "primary_tenant"
        ).prefetch_related(
            "co_tenants__person", "occupants__person", "guarantors__person", "documents"
        )
        if user.role == User.Role.TENANT:
            from apps.tenant_portal.views import get_tenant_leases

            return qs.filter(pk__in=get_tenant_leases(user).values_list("pk", flat=True))
        if user.role == User.Role.ADMIN:
            return qs
        # All staff roles: scope to accessible properties
        from apps.properties.access import get_accessible_property_ids
        prop_ids = get_accessible_property_ids(user)
        return qs.filter(unit__property_id__in=prop_ids)

    # ------------------------------------------------------------------ #
    # Documents
    # ------------------------------------------------------------------ #

    @action(detail=True, methods=["get", "post"], url_path="documents")
    def documents(self, request, pk=None):
        lease = self.get_object()
        if request.method == "GET":
            serializer = LeaseDocumentSerializer(
                lease.documents.all(), many=True, context={"request": request}
            )
            return Response(serializer.data)

        uploaded_file = request.FILES.get("file")
        if uploaded_file:
            fname = uploaded_file.name
            if lease.documents.filter(description=fname).exists():
                existing = LeaseDocumentSerializer(
                    lease.documents.filter(description=fname).first(),
                    context={"request": request},
                )
                return Response(existing.data, status=status.HTTP_200_OK)

        serializer = LeaseDocumentSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save(lease=lease)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path="documents/(?P<doc_id>[^/.]+)")
    def delete_document(self, request, pk=None, doc_id=None):
        lease = self.get_object()
        doc = get_object_or_404(LeaseDocument, pk=doc_id, lease=lease)
        try:
            doc.file.delete(save=False)
        except Exception:
            pass
        doc.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ------------------------------------------------------------------ #
    # Tenants
    # ------------------------------------------------------------------ #

    @action(detail=True, methods=["post"], url_path="tenants")
    def add_tenant(self, request, pk=None):
        lease = self.get_object()
        person_id = request.data.get("person_id")
        if person_id:
            person = get_object_or_404(Person, pk=person_id)
        else:
            person_data = request.data.get("person", {})
            s = PersonSerializer(data=person_data)
            s.is_valid(raise_exception=True)
            person = s.save()

        if not lease.primary_tenant:
            lease.primary_tenant = person
            lease.save(update_fields=["primary_tenant"])
        else:
            LeaseTenant.objects.get_or_create(lease=lease, person=person)

        return Response(PersonSerializer(person).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path="tenants/(?P<person_id>[^/.]+)")
    def remove_tenant(self, request, pk=None, person_id=None):
        lease = self.get_object()
        deleted, _ = LeaseTenant.objects.filter(lease=lease, person_id=person_id).delete()
        if deleted == 0 and lease.primary_tenant_id == int(person_id):
            first_co = lease.co_tenants.select_related("person").first()
            if first_co:
                lease.primary_tenant = first_co.person
                lease.save(update_fields=["primary_tenant"])
                first_co.delete()
            else:
                lease.primary_tenant = None
                lease.save(update_fields=["primary_tenant"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ------------------------------------------------------------------ #
    # Occupants
    # ------------------------------------------------------------------ #

    @action(detail=True, methods=["post"], url_path="occupants")
    def add_occupant(self, request, pk=None):
        lease = self.get_object()
        person_id = request.data.get("person_id")
        if person_id:
            person = get_object_or_404(Person, pk=person_id)
        else:
            s = PersonSerializer(data=request.data.get("person", {}))
            s.is_valid(raise_exception=True)
            person = s.save()
        relationship = request.data.get("relationship_to_tenant", "")
        occ, created = LeaseOccupant.objects.get_or_create(
            lease=lease, person=person,
            defaults={"relationship_to_tenant": relationship},
        )
        if not created:
            occ.relationship_to_tenant = relationship
            occ.save(update_fields=["relationship_to_tenant"])
        return Response(LeaseOccupantSerializer(occ).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path="occupants/(?P<occupant_id>[^/.]+)")
    def remove_occupant(self, request, pk=None, occupant_id=None):
        lease = self.get_object()
        occ = get_object_or_404(LeaseOccupant, pk=occupant_id, lease=lease)
        occ.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ------------------------------------------------------------------ #
    # Guarantors
    # ------------------------------------------------------------------ #

    @action(detail=True, methods=["post"], url_path="guarantors")
    def add_guarantor(self, request, pk=None):
        lease = self.get_object()
        person_id = request.data.get("person_id")
        if person_id:
            person = get_object_or_404(Person, pk=person_id)
        else:
            s = PersonSerializer(data=request.data.get("person", {}))
            s.is_valid(raise_exception=True)
            person = s.save()
        covers_tenant_id = request.data.get("covers_tenant_id")
        covers = Person.objects.filter(pk=covers_tenant_id).first() if covers_tenant_id else None
        gua = LeaseGuarantor.objects.create(lease=lease, person=person, covers_tenant=covers)
        return Response(LeaseGuarantorSerializer(gua).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path="guarantors/(?P<guarantor_id>[^/.]+)")
    def remove_guarantor(self, request, pk=None, guarantor_id=None):
        lease = self.get_object()
        gua = get_object_or_404(LeaseGuarantor, pk=guarantor_id, lease=lease)
        gua.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ── Lease Events ──

    @action(detail=True, methods=["get", "post"], url_path="events")
    def events(self, request, pk=None):
        lease = self.get_object()
        if request.method == "GET":
            qs = lease.events.all()
            return Response(LeaseEventSerializer(qs, many=True).data)
        # POST — create custom event
        serializer = LeaseEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(lease=lease, event_type=LeaseEvent.EventType.CUSTOM)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["patch"], url_path="events/(?P<event_id>[^/.]+)")
    def update_event(self, request, pk=None, event_id=None):
        lease = self.get_object()
        event = get_object_or_404(LeaseEvent, pk=event_id, lease=lease)
        serializer = LeaseEventSerializer(event, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        if request.data.get("status") == "completed" and not event.completed_at:
            from django.utils import timezone
            serializer.save(completed_at=timezone.now(), completed_by=request.user)
        else:
            serializer.save()
        return Response(serializer.data)

    # ------------------------------------------------------------------ #
    # Renewal — create a pending successor lease that follows this one.
    # Copies property/unit/rent/deposit/terms; does NOT copy tenants.
    # ------------------------------------------------------------------ #

    @action(detail=True, methods=["post"], url_path="renewal")
    def renewal(self, request, pk=None):
        source = self.get_object()

        existing_successor = source.successor_lease.first()
        if existing_successor:
            serializer = LeaseSerializer(existing_successor, context={"request": request})
            return Response(
                {"detail": "Renewal already exists.", "lease": serializer.data},
                status=status.HTTP_409_CONFLICT,
            )

        if not source.end_date:
            return Response(
                {"error": "Source lease has no end_date — cannot schedule a renewal."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        overrides = request.data if isinstance(request.data, dict) else {}

        default_start = source.end_date + timedelta(days=1)
        # 12-month default span, end_date is exclusive of the start_date anniversary — use -1 day.
        default_end = default_start.replace(year=default_start.year + 1) - timedelta(days=1)

        def _pick(key, fallback):
            v = overrides.get(key)
            return v if v not in (None, "") else fallback

        with transaction.atomic():
            new_lease = Lease.objects.create(
                unit=source.unit,
                previous_lease=source,
                status=Lease.Status.PENDING,
                start_date=_pick("start_date", default_start),
                end_date=_pick("end_date", default_end),
                monthly_rent=_pick("monthly_rent", source.monthly_rent),
                deposit=_pick("deposit", source.deposit),
                max_occupants=_pick("max_occupants", source.max_occupants),
                water_included=_pick("water_included", source.water_included),
                water_limit_litres=_pick("water_limit_litres", source.water_limit_litres),
                electricity_prepaid=_pick("electricity_prepaid", source.electricity_prepaid),
                notice_period_days=_pick("notice_period_days", source.notice_period_days),
                early_termination_penalty_months=_pick(
                    "early_termination_penalty_months",
                    source.early_termination_penalty_months,
                ),
                rent_due_day=_pick("rent_due_day", source.rent_due_day),
                payment_reference=_pick("payment_reference", source.payment_reference),
            )

        serializer = LeaseSerializer(new_lease, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="generate-events")
    def generate_events(self, request, pk=None):
        """Auto-generate calendar events for this lease."""
        lease = self.get_object()
        events = generate_lease_events(lease)
        onboarding = generate_onboarding_steps(lease)
        return Response({
            "events_created": len(events),
            "onboarding_steps_created": len(onboarding),
        })

    # ── Onboarding ──

    @action(detail=True, methods=["get"], url_path="onboarding")
    def onboarding(self, request, pk=None):
        lease = self.get_object()
        qs = lease.onboarding_steps.all()
        return Response(OnboardingStepSerializer(qs, many=True).data)

    @action(detail=True, methods=["patch"], url_path="onboarding/(?P<step_id>[^/.]+)")
    def update_onboarding(self, request, pk=None, step_id=None):
        lease = self.get_object()
        step = get_object_or_404(OnboardingStep, pk=step_id, lease=lease)
        if request.data.get("is_completed") and not step.completed_at:
            from django.utils import timezone
            step.is_completed = True
            step.completed_at = timezone.now()
            step.completed_by = request.user
        elif request.data.get("is_completed") is False:
            step.is_completed = False
            step.completed_at = None
            step.completed_by = None
        if "notes" in request.data:
            step.notes = request.data["notes"]
        step.save()
        return Response(OnboardingStepSerializer(step).data)

    # ── Inventory ──

    @action(detail=True, methods=["get", "post"], url_path="inventory")
    def inventory(self, request, pk=None):
        lease = self.get_object()
        if request.method == "GET":
            return Response(InventoryItemSerializer(lease.inventory_items.all(), many=True).data)
        serializer = InventoryItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(lease=lease)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["patch", "delete"], url_path="inventory/(?P<item_id>[^/.]+)")
    def update_inventory_item(self, request, pk=None, item_id=None):
        lease = self.get_object()
        item = get_object_or_404(InventoryItem, pk=item_id, lease=lease)
        if request.method == "DELETE":
            item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = InventoryItemSerializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="inventory/from-template")
    def inventory_from_template(self, request, pk=None):
        """Copy items from a template into this lease's inventory."""
        lease = self.get_object()
        template_id = request.data.get("template_id")
        tmpl = get_object_or_404(InventoryTemplate, pk=template_id)
        created = []
        for item_data in tmpl.items:
            created.append(InventoryItem.objects.create(
                lease=lease,
                name=item_data.get("name", ""),
                category=item_data.get("category", "other"),
                quantity=item_data.get("qty", 1),
                notes=item_data.get("notes", ""),
            ))
        return Response({
            "items_created": len(created),
            "items": InventoryItemSerializer(created, many=True).data,
        }, status=status.HTTP_201_CREATED)


class InventoryTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = InventoryTemplateSerializer
    permission_classes = [IsAuthenticated]
    queryset = InventoryTemplate.objects.all()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class LeaseCalendarView:
    """Standalone view for calendar across all leases."""
    pass


from rest_framework.views import APIView


class LeaseCalendarAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        from_date = request.query_params.get("from")
        to_date = request.query_params.get("to")
        qs = LeaseEvent.objects.select_related("lease__unit__property", "lease__primary_tenant")
        if user.role == User.Role.AGENT:
            from apps.properties.access import get_accessible_property_ids
            prop_ids = get_accessible_property_ids(user)
            qs = qs.filter(lease__unit__property_id__in=prop_ids)
        elif user.role != User.Role.ADMIN:
            qs = qs.none()
        if from_date:
            qs = qs.filter(date__gte=from_date)
        if to_date:
            qs = qs.filter(date__lte=to_date)
        return Response(LeaseEventSerializer(qs, many=True).data)
