from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import Person, User
from .models import Lease, LeaseDocument, LeaseTenant, LeaseOccupant, LeaseGuarantor, LeaseEvent, OnboardingStep
from .serializers import (
    LeaseSerializer, LeaseDocumentSerializer,
    LeaseOccupantSerializer, LeaseGuarantorSerializer, PersonSerializer,
    LeaseEventSerializer, OnboardingStepSerializer,
)


class LeaseViewSet(viewsets.ModelViewSet):
    serializer_class = LeaseSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["status", "unit"]

    def perform_create(self, serializer):
        lease = serializer.save()
        from .events import generate_lease_events, generate_onboarding_steps
        generate_lease_events(lease)
        generate_onboarding_steps(lease)

    def perform_update(self, serializer):
        old_status = serializer.instance.status
        lease = serializer.save()
        # Regenerate events when lease becomes active or dates change
        if lease.status == Lease.Status.ACTIVE and old_status != Lease.Status.ACTIVE:
            from .events import generate_lease_events, generate_onboarding_steps
            generate_lease_events(lease)
            generate_onboarding_steps(lease)

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
        if user.role == User.Role.AGENT:
            # Same portfolio scope as maintenance for assigned properties; include
            # unassigned properties; and properties still tied to an admin user from
            # older imports (before import stopped setting agent=request.user for admins).
            return qs.filter(
                Q(unit__property__agent=user)
                | Q(unit__property__agent__isnull=True)
                | Q(unit__property__agent__role=User.Role.ADMIN)
            ).distinct()
        return qs.none()

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

    # ------------------------------------------------------------------ #
    # Events
    # ------------------------------------------------------------------ #

    @action(detail=True, methods=["get", "post"], url_path="events")
    def events(self, request, pk=None):
        lease = self.get_object()
        if request.method == "GET":
            serializer = LeaseEventSerializer(lease.events.all(), many=True)
            return Response(serializer.data)
        # POST — create custom event
        data = {**request.data, "event_type": LeaseEvent.EventType.CUSTOM}
        serializer = LeaseEventSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(lease=lease)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["patch"], url_path="events/(?P<event_id>[^/.]+)")
    def update_event(self, request, pk=None, event_id=None):
        lease = self.get_object()
        event = get_object_or_404(LeaseEvent, pk=event_id, lease=lease)
        serializer = LeaseEventSerializer(event, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        if request.data.get("status") == LeaseEvent.Status.COMPLETED and not event.completed_at:
            serializer.save(completed_at=timezone.now(), completed_by=request.user)
        else:
            serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="calendar")
    def calendar(self, request):
        """All lease events across accessible leases, optionally filtered by date range."""
        qs = self.get_queryset()
        from_date = request.query_params.get("from")
        to_date = request.query_params.get("to")
        events_qs = LeaseEvent.objects.filter(lease__in=qs).select_related("lease__unit__property", "lease__primary_tenant")
        if from_date:
            events_qs = events_qs.filter(date__gte=from_date)
        if to_date:
            events_qs = events_qs.filter(date__lte=to_date)

        class CalendarEventSerializer(LeaseEventSerializer):
            lease_label = serializers.SerializerMethodField()
            tenant_name = serializers.SerializerMethodField()
            property_name = serializers.SerializerMethodField()

            class Meta(LeaseEventSerializer.Meta):
                fields = LeaseEventSerializer.Meta.fields + ["lease_label", "tenant_name", "property_name", "lease"]

            def get_lease_label(self, obj):
                return str(obj.lease)

            def get_tenant_name(self, obj):
                return obj.lease.primary_tenant.full_name if obj.lease.primary_tenant else ""

            def get_property_name(self, obj):
                try:
                    return obj.lease.unit.property.name
                except Exception:
                    return ""

        from rest_framework import serializers as drf_serializers
        CalendarEventSerializer.lease_label = drf_serializers.SerializerMethodField()
        CalendarEventSerializer.tenant_name = drf_serializers.SerializerMethodField()
        CalendarEventSerializer.property_name = drf_serializers.SerializerMethodField()

        result = []
        for ev in events_qs.order_by("date"):
            result.append({
                "id": ev.id,
                "lease": ev.lease_id,
                "event_type": ev.event_type,
                "title": ev.title,
                "description": ev.description,
                "date": str(ev.date),
                "status": ev.status,
                "is_recurring": ev.is_recurring,
                "tenant_name": ev.lease.primary_tenant.full_name if ev.lease.primary_tenant else "",
                "property_name": getattr(getattr(getattr(ev.lease, "unit", None), "property", None), "name", ""),
            })
        return Response(result)

    @action(detail=True, methods=["post"], url_path="generate-events")
    def generate_events(self, request, pk=None):
        """Manually trigger event + onboarding generation for a lease."""
        lease = self.get_object()
        from .events import generate_lease_events, generate_onboarding_steps
        generate_lease_events(lease)
        generate_onboarding_steps(lease)
        return Response({"detail": "Events and onboarding steps generated."})

    # ------------------------------------------------------------------ #
    # Onboarding
    # ------------------------------------------------------------------ #

    @action(detail=True, methods=["get"], url_path="onboarding")
    def onboarding(self, request, pk=None):
        lease = self.get_object()
        serializer = OnboardingStepSerializer(lease.onboarding_steps.all(), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["patch"], url_path="onboarding/(?P<step_id>[^/.]+)")
    def update_onboarding(self, request, pk=None, step_id=None):
        lease = self.get_object()
        step = get_object_or_404(OnboardingStep, pk=step_id, lease=lease)
        serializer = OnboardingStepSerializer(step, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        if request.data.get("is_completed") and not step.completed_at:
            serializer.save(completed_at=timezone.now(), completed_by=request.user)
        else:
            serializer.save()
        return Response(serializer.data)
