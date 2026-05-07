import logging
from datetime import timedelta
from django.db import transaction
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import Person, User
from apps.accounts.permissions import IsAgentOrAdmin
from apps.accounts.scoping import AgencyScopedQuerysetMixin, AgencyStampedCreateMixin
from .models import Lease, LeaseDocument, LeaseEvent, LeaseTenant, LeaseOccupant, LeaseGuarantor, OnboardingStep, InventoryItem, InventoryTemplate, MoveInChecklistItem, MOVE_IN_CHECKLIST_DEFAULTS
from .serializers import (
    LeaseSerializer, LeaseDocumentSerializer, LeaseEventSerializer,
    LeaseOccupantSerializer, LeaseGuarantorSerializer, OnboardingStepSerializer, PersonSerializer,
    LeaseTenantSerializer,
    InventoryItemSerializer, InventoryTemplateSerializer, MoveInChecklistItemSerializer,
)
from .events import generate_lease_events, generate_onboarding_steps

logger = logging.getLogger(__name__)


class LeaseViewSet(AgencyScopedQuerysetMixin, AgencyStampedCreateMixin, viewsets.ModelViewSet):
    queryset = Lease.objects.all()
    serializer_class = LeaseSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["status", "unit", "primary_tenant"]

    # Write actions are restricted to agents and admins.
    # Owners and tenants may list and retrieve but must not mutate leases.
    _WRITE_ACTIONS = {"create", "update", "partial_update", "destroy"}

    def get_permissions(self):
        if self.action in self._WRITE_ACTIONS:
            return [IsAgentOrAdmin()]
        return super().get_permissions()

    def perform_destroy(self, instance):
        for doc in instance.documents.all():
            try:
                doc.file.delete(save=False)
            except Exception:
                logger.exception("Failed to delete lease document file %s", doc.pk)
        instance.delete()

    def get_queryset(self):
        user = self.request.user
        # Tenants are cross-tenant by design — they don't have an agency_id but
        # they DO have access to their own lease records via Person/User links.
        # Bypass the agency filter for them and use the tenant-portal helper.
        if getattr(user, "role", None) == User.Role.TENANT:
            from apps.tenant_portal.views import get_tenant_leases
            qs = Lease.objects.select_related(
                "unit__property", "unit__property__agent", "primary_tenant"
            ).prefetch_related(
                "co_tenants__person", "occupants__person", "guarantors__person", "documents",
                "move_in_checklist__completed_by",
            )
            return qs.filter(pk__in=get_tenant_leases(user).values_list("pk", flat=True))

        # Staff path — route through AgencyScopedQuerysetMixin first
        # (admin bypass; .none() for non-admin without agency).
        base = super().get_queryset().select_related(
            "unit__property", "unit__property__agent", "primary_tenant"
        ).prefetch_related(
            "co_tenants__person", "occupants__person", "guarantors__person", "documents",
            "move_in_checklist__completed_by",
        )
        if user.role == User.Role.ADMIN:
            return base
        # All staff roles: scope to accessible properties (defence in depth on top of agency).
        from apps.properties.access import get_accessible_property_ids
        prop_ids = get_accessible_property_ids(user)
        return base.filter(unit__property_id__in=prop_ids)

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
        serializer.save(lease=lease, agency_id=lease.agency_id)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path="documents/(?P<doc_id>[^/.]+)")
    def delete_document(self, request, pk=None, doc_id=None):
        lease = self.get_object()
        doc = get_object_or_404(LeaseDocument, pk=doc_id, lease=lease)
        try:
            doc.file.delete(save=False)
        except Exception:
            logger.exception("Failed to delete lease document file %s", doc.pk)
        doc.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ------------------------------------------------------------------ #
    # Tenants
    # ------------------------------------------------------------------ #

    @action(detail=True, methods=["post"], url_path="tenants")
    def add_tenant(self, request, pk=None):
        lease = self.get_object()
        person_id = request.data.get("person_id")
        # Persons are agency-scoped (Phase 4). Bind the lease's agency so we
        # neither leak across tenants on lookup nor stamp NULL on create.
        agency_id = lease.agency_id
        if person_id:
            person = get_object_or_404(Person, pk=person_id, agency_id=agency_id)
        else:
            person_data = request.data.get("person", {})
            s = PersonSerializer(data=person_data)
            s.is_valid(raise_exception=True)
            person = s.save(agency_id=agency_id)

        payment_reference = (request.data.get("payment_reference") or "").strip()

        if not lease.primary_tenant:
            lease.primary_tenant = person
            update_fields = ["primary_tenant"]
            if payment_reference:
                lease.payment_reference = payment_reference
                update_fields.append("payment_reference")
            lease.save(update_fields=update_fields)
        else:
            ct, created = LeaseTenant.objects.get_or_create(
                lease=lease, person=person,
                defaults={
                    "agency_id": lease.agency_id,
                    "payment_reference": payment_reference,
                },
            )
            if not created and payment_reference and ct.payment_reference != payment_reference:
                ct.payment_reference = payment_reference
                ct.save(update_fields=["payment_reference"])

        return Response(PersonSerializer(person).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["patch"], url_path="co-tenants/(?P<co_tenant_id>[^/.]+)")
    def update_co_tenant(self, request, pk=None, co_tenant_id=None):
        """
        PATCH /api/v1/leases/{id}/co-tenants/{co_tenant_id}/

        Update LeaseTenant fields (currently only ``payment_reference``).
        """
        lease = self.get_object()
        ct = get_object_or_404(LeaseTenant, pk=co_tenant_id, lease=lease)
        if "payment_reference" in request.data:
            ct.payment_reference = request.data.get("payment_reference") or ""
            ct.save(update_fields=["payment_reference"])
        return Response(LeaseTenantSerializer(ct).data)

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
            defaults={
                "agency_id": lease.agency_id,
                "relationship_to_tenant": relationship,
            },
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
        gua = LeaseGuarantor.objects.create(
            agency_id=lease.agency_id, lease=lease,
            person=person, covers_tenant=covers,
        )
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
        serializer.save(lease=lease, agency_id=lease.agency_id, event_type=LeaseEvent.EventType.CUSTOM)
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
                agency=source.agency,
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

    # ── RHA compliance gate ──

    @action(detail=True, methods=["get"], url_path="rha-check")
    def rha_check(self, request, pk=None):
        """
        GET /api/v1/leases/{id}/rha-check/

        Refresh RHA compliance flags for this lease and return the current flag
        list split into blocking and advisory categories.
        """
        from apps.leases.rha_check import blocking_flags, advisory_flags

        lease = self.get_object()
        # Use refresh_rha_flags() so that any stale override is invalidated
        # when the blocking flag set has changed since the override was recorded.
        flags = lease.refresh_rha_flags()

        # POPIA: rha_override stores the staff member's user_id and email.
        # Only authorised internal users may see the full blob; tenants and
        # other non-staff callers receive a redacted summary instead.
        _allowed_roles = {"agency_admin", "admin"}
        _caller_is_staff = (
            request.user.is_staff
            or request.user.is_superuser
            or getattr(request.user, "role", None) in _allowed_roles
        )
        if _caller_is_staff:
            override_payload = lease.rha_override
        elif lease.rha_override:
            override_payload = {
                "override_recorded": True,
                "overridden_at": lease.rha_override.get("overridden_at"),
            }
        else:
            override_payload = None

        return Response({
            "lease_id": lease.pk,
            "flags": flags,
            "blocking": blocking_flags(flags),
            "advisory": advisory_flags(flags),
            "override": override_payload,
        })

    @action(detail=True, methods=["post"], url_path="rha-override")
    def rha_override(self, request, pk=None):
        """
        POST /api/v1/leases/{id}/rha-override/

        Record a staff-authorised override for the current blocking RHA flags.
        Requires ``is_staff``, ``is_superuser``, or ``role == 'agency_admin'``.

        Body: { "reason": "<non-empty explanation>" }
        """
        lease = self.get_object()
        reason = (request.data.get("reason") or "").strip()

        try:
            lease.record_rha_override(request.user, reason)
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        # POPIA: the full override blob contains staff user_id and email.
        # Return the complete blob here — this endpoint is already restricted
        # to authorised staff/agency_admin callers (enforced by record_rha_override),
        # so the caller is always permitted to see the full payload.
        return Response({
            "detail": "RHA override recorded.",
            "override": lease.rha_override,
        })

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

    # ── Move-in checklist ──

    @action(detail=True, methods=["get"], url_path="move-in-checklist")
    def move_in_checklist(self, request, pk=None):
        """
        GET /api/v1/leases/<id>/move-in-checklist/

        Returns all move-in checklist items for this lease, seeding the defaults
        if none exist yet. Visible to agents (read/write) and owners (read-only).
        """
        lease = self.get_object()
        self._ensure_checklist_seeded(lease)
        items = lease.move_in_checklist.select_related("completed_by").all()
        return Response(MoveInChecklistItemSerializer(items, many=True).data)

    @action(detail=True, methods=["patch"], url_path="move-in-checklist/(?P<item_key>[^/.]+)")
    def toggle_move_in_item(self, request, pk=None, item_key=None):
        """
        PATCH /api/v1/leases/<id>/move-in-checklist/<key>/

        Toggle a checklist item's completion state.
        Body: { "is_completed": true|false }
        Only agents and admins may mutate; owners receive 403.
        """
        from apps.accounts.models import User as AuthUser
        user = request.user

        # Owner role is read-only for the checklist
        if user.role == AuthUser.Role.OWNER:
            return Response(
                {"detail": "Owners may not modify the move-in checklist."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # All other non-agent roles also blocked (tenants, suppliers, etc.)
        agent_roles = {
            AuthUser.Role.AGENT, AuthUser.Role.ESTATE_AGENT,
            AuthUser.Role.MANAGING_AGENT, AuthUser.Role.AGENCY_ADMIN, AuthUser.Role.ADMIN,
        }
        if user.role not in agent_roles:
            return Response(
                {"detail": "Only agents and admins may modify the move-in checklist."},
                status=status.HTTP_403_FORBIDDEN,
            )

        lease = self.get_object()
        self._ensure_checklist_seeded(lease)
        item = get_object_or_404(MoveInChecklistItem, lease=lease, key=item_key)

        is_completed = request.data.get("is_completed")
        if is_completed is None:
            return Response(
                {"detail": "is_completed is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.utils import timezone as tz
        if is_completed:
            item.is_completed = True
            if not item.completed_at:
                item.completed_at = tz.now()
                item.completed_by = user
        else:
            item.is_completed = False
            item.completed_at = None
            item.completed_by = None

        item.save(update_fields=["is_completed", "completed_at", "completed_by"])
        return Response(MoveInChecklistItemSerializer(item).data)

    @staticmethod
    def _ensure_checklist_seeded(lease):
        """Create default checklist items for this lease if they don't exist yet."""
        existing_keys = set(
            lease.move_in_checklist.values_list("key", flat=True)
        )
        to_create = [
            MoveInChecklistItem(lease=lease, agency_id=lease.agency_id, key=key)
            for key in MOVE_IN_CHECKLIST_DEFAULTS
            if key not in existing_keys
        ]
        if to_create:
            MoveInChecklistItem.objects.bulk_create(to_create, ignore_conflicts=True)
            # Refresh the prefetch cache
            lease.move_in_checklist._result_cache = None

    # ── Inventory ──

    @action(detail=True, methods=["get", "post"], url_path="inventory")
    def inventory(self, request, pk=None):
        lease = self.get_object()
        if request.method == "GET":
            return Response(InventoryItemSerializer(lease.inventory_items.all(), many=True).data)
        serializer = InventoryItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(lease=lease, agency_id=lease.agency_id)
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
                agency_id=lease.agency_id,
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


class InventoryTemplateViewSet(
    AgencyScopedQuerysetMixin, AgencyStampedCreateMixin, viewsets.ModelViewSet
):
    serializer_class = InventoryTemplateSerializer
    permission_classes = [IsAuthenticated]
    queryset = InventoryTemplate.objects.all()

    def perform_create(self, serializer):
        # Stamp agency via super().perform_create — it consumes serializer.save() with
        # agency_id; then patch the created_by user on the instance.
        # Pass created_by through serializer.save() by calling save twice would duplicate;
        # instead, call the mixin's logic but pass created_by alongside agency.
        user = getattr(self.request, "user", None)
        agency_id = getattr(user, "agency_id", None)
        from apps.accounts.scoping import _is_admin
        from rest_framework.exceptions import ValidationError
        if _is_admin(user):
            agency_id = serializer.validated_data.get("agency_id") or agency_id
            if agency_id is None:
                raise ValidationError(
                    {"agency": "Admin user must specify `agency` when creating without an agency_id of their own."}
                )
            serializer.save(agency_id=agency_id, created_by=user)
            return
        if agency_id is None:
            raise ValidationError(
                {"detail": "Your user account is not linked to an agency. Contact your administrator."}
            )
        serializer.save(agency_id=agency_id, created_by=user)


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
        # Agency scoping (Phase 2.4) — admin bypasses, everyone else is restricted
        # to their own agency_id; users without an agency see nothing.
        if user.role != User.Role.ADMIN:
            agency_id = getattr(user, "agency_id", None)
            if agency_id is None:
                qs = qs.none()
            else:
                qs = qs.filter(agency_id=agency_id)
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
