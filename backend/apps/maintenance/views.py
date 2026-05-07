from django.db.models import Count, Exists, OuterRef, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated

from apps.accounts.permissions import IsAgentOrAdmin, IsTenantOrAgent
from apps.accounts.scoping import (
    AgencyScopedQuerysetMixin,
    AgencyStampedCreateMixin,
    _is_admin,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from .matching import rank_suppliers
from .chat_history import persist_chat_history_to_request
from .models import (
    AgentQuestion, JobDispatch, JobQuote, JobQuoteRequest,
    MaintenanceActivity, MaintenanceRequest, MaintenanceSkill, Supplier, SupplierDocument,
    SupplierInvoice, SupplierProperty, SupplierTrade,
)
from .notifications import notify_supplier
from .serializers import (
    AgentQuestionSerializer,
    JobDispatchSerializer,
    JobQuoteRequestSerializer,
    JobQuoteSerializer,
    MaintenanceActivitySerializer,
    MaintenanceRequestSerializer,
    MaintenanceSkillSerializer,
    SupplierDocumentSerializer,
    SupplierListSerializer,
    SupplierPropertySerializer,
    SupplierQuotePageSerializer,
    SupplierSerializer,
)


class MaintenanceRequestViewSet(AgencyScopedQuerysetMixin, AgencyStampedCreateMixin, viewsets.ModelViewSet):
    """
    CRUD endpoint for maintenance requests.

    Role-based write guards (POPIA compliance):
    - Suppliers may only interact with jobs dispatched to them via the supplier
      portal; they must never create or inject maintenance requests on behalf of
      tenants.  Only tenants and agent-variant roles (including admin) may POST
      new requests.

    Phase 2.5 tenant scoping
    ------------------------
    Tenants legitimately read/create their own maintenance requests and they
    do NOT belong to an agency, so the AgencyScopedQuerysetMixin would return
    .none() for them. We bypass the mixin filter for tenant-role users (they
    are already filtered to ``tenant=request.user``). Agency staff are scoped
    via the mixin then layered with the existing property-access filter.
    """

    queryset = MaintenanceRequest.objects.all()
    serializer_class = MaintenanceRequestSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["status", "priority", "unit", "supplier"]

    # Actions that mutate dispatch / awarding state must be agent-only.
    _AGENT_ONLY_ACTIONS = {"dispatch_award", "dispatch_send", "job_dispatch"}

    def get_permissions(self):
        if self.action == "create":
            # Suppliers must not create maintenance requests — they interact only
            # with jobs dispatched to them (POPIA data-minimisation principle).
            # Owners are also excluded: only tenants and agent-variant roles may POST.
            return [IsTenantOrAgent()]
        if self.action in ("update", "partial_update", "destroy"):
            # Owners and tenants are read-only on the agent-facing API.
            # Only agents and admins may mutate or delete existing requests.
            return [IsAgentOrAdmin()]
        if self.action in self._AGENT_ONLY_ACTIONS:
            # job_dispatch handles both GET (read) and POST (mutate).
            # Only lock down the mutating POST; GET stays IsAuthenticated.
            if self.action == "job_dispatch" and self.request.method == "GET":
                return [IsAuthenticated()]
            return [IsAgentOrAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        # Tenants legitimately access maintenance they reported but have no
        # agency_id; bypass the agency mixin and filter by tenant=user
        # instead. All other roles flow through super().get_queryset() which
        # applies the AgencyScopedQuerysetMixin (admin → all; agency users →
        # their agency only; users with no agency → .none()).
        if hasattr(user, "role") and user.role == "tenant":
            qs = MaintenanceRequest.objects.filter(tenant=user)
        else:
            qs = super().get_queryset()
            # Layer the existing property-access filter on top for non-admin
            # agency staff (defence in depth).
            if hasattr(user, "role") and user.role != "admin" and not getattr(user, "is_superuser", False):
                from apps.properties.access import get_accessible_property_ids
                prop_ids = get_accessible_property_ids(user)
                qs = qs.filter(unit__property_id__in=prop_ids)
        qs = qs.select_related("supplier", "tenant").annotate(
            activity_count=Count("activities"),
        ).order_by("-created_at")
        property_id = self.request.query_params.get("property")
        if property_id:
            qs = qs.filter(unit__property_id=property_id)
        exclude_status = self.request.query_params.get("exclude_status")
        if exclude_status:
            qs = qs.exclude(status=exclude_status)
        return qs

    def perform_create(self, serializer):
        """Stamp agency_id correctly across the tenant + agency-staff paths.

        Tenants have no agency_id of their own — derive it from the unit's
        property. The serializer's own ``create()`` resolves the unit when
        the tenant doesn't pass one, so we must not depend on the validated
        ``unit`` being set here. For non-tenant callers, fall through to
        AgencyStampedCreateMixin.
        """
        user = self.request.user
        if hasattr(user, "role") and user.role == "tenant":
            # Pre-resolve the unit (mirrors serializer logic) so we can stamp
            # agency_id without waiting for serializer.create().
            unit = serializer.validated_data.get("unit")
            if unit is None:
                # Defer to serializer.create — it will resolve and may raise.
                # We can't compute agency in advance; instead let the
                # serializer commit and patch the row afterwards.
                obj = serializer.save()
                resolved_unit_id = obj.unit_id
                if obj.agency_id is None and resolved_unit_id is not None:
                    from apps.properties.models import Unit
                    agency_id = (
                        Unit.objects.filter(pk=resolved_unit_id)
                        .values_list("agency_id", flat=True)
                        .first()
                    )
                    if agency_id is not None:
                        type(obj).objects.filter(pk=obj.pk).update(agency_id=agency_id)
                        obj.agency_id = agency_id
                return
            agency_id = getattr(unit, "agency_id", None)
            if agency_id is None:
                agency_id = getattr(getattr(unit, "property", None), "agency_id", None)
            serializer.save(agency_id=agency_id)
            return
        super().perform_create(serializer)


    @action(detail=False, methods=["post"], url_path="classify")
    def classify(self, request):
        """
        RAG-based classification: suggest category and priority from past issues.

        POST { "title": "...", "description": "...", "property_id": 123 }
        Returns { "category", "priority", "confidence", "rag_matches", "skill_matches" }
        """
        from core.contract_rag import classify_from_rag
        title = (request.data.get("title") or "").strip()
        description = (request.data.get("description") or "").strip()
        query = f"{title} {description}".strip()
        if len(query) < 5:
            return Response({"error": "title or description required"}, status=status.HTTP_400_BAD_REQUEST)
        property_id = request.data.get("property_id")
        result = classify_from_rag(query, property_id=property_id)
        return Response(result)

    @action(detail=False, methods=["get"], url_path="badges")
    def badges(self, request):
        """
        Lightweight counts for sidebar badge indicators.

        Badge counting rules
        -------------------
        open_issues
            Counts MaintenanceRequest rows with status ``open`` or
            ``in_progress`` — tickets that actively need attention.
            Resolved and closed tickets are intentionally excluded because
            they no longer require agent action.

            The queryset is scoped using ``get_queryset()`` so the count
            always reflects exactly the same set of records the user can
            see in the list view:
              - Tenants see only their own requests.
              - Non-admin agents see only requests for properties in their
                accessible portfolio (``get_accessible_property_ids``).
              - Admin users see all requests.

        pending_questions
            Counts AgentQuestion rows with status ``pending`` scoped to the
            same accessible property set (non-admin users) so agents only
            see questions raised against their own portfolio.
        """
        # Reuse get_queryset() to get the fully-scoped queryset (role-based
        # property access, tenant isolation, admin sees all).  Then narrow to
        # the "active" statuses that represent tickets needing attention.
        scoped_qs = self.get_queryset()
        open_issues = scoped_qs.filter(
            status__in=[
                MaintenanceRequest.Status.OPEN,
                MaintenanceRequest.Status.IN_PROGRESS,
            ]
        ).count()

        # Scope AgentQuestion to the same accessible property set.
        user = request.user
        q_qs = AgentQuestion.objects.filter(status=AgentQuestion.Status.PENDING)
        if hasattr(user, "role") and user.role != "admin":
            if user.role == "tenant":
                # Tenants never see agent questions — return 0.
                q_qs = AgentQuestion.objects.none()
            else:
                from apps.properties.access import get_accessible_property_ids
                prop_ids = get_accessible_property_ids(user)
                # Questions without a linked property are visible to agents.
                q_qs = q_qs.filter(
                    Q(property_id__in=prop_ids) | Q(property__isnull=True)
                )
        pending_questions = q_qs.count()

        return Response({
            "open_issues": open_issues,
            "pending_questions": pending_questions,
        })

    @action(detail=False, methods=["get"], url_path="overdue")
    def overdue(self, request):
        """
        Return overdue maintenance tickets scoped to the requesting user.

        Overdue = resolve deadline has passed AND ticket is open / in_progress.
        Owner users see only tickets for their properties.
        Agents see all tickets in their accessible properties.
        """
        now = timezone.now()
        qs = MaintenanceRequest.objects.filter(
            sla_resolve_deadline__lt=now,
            status__in=[MaintenanceRequest.Status.OPEN, MaintenanceRequest.Status.IN_PROGRESS],
        ).select_related("unit__property", "tenant", "supplier").order_by("sla_resolve_deadline")

        user = request.user
        if hasattr(user, "role"):
            if user.role == "tenant":
                qs = qs.filter(tenant=user)
            elif user.role == "owner":
                # Filter to properties owned by this user
                from apps.properties.models import Property
                owned = Property.objects.filter(owner=user).values_list("id", flat=True)
                qs = qs.filter(unit__property_id__in=list(owned))
            elif user.role not in ("admin", "agency_admin"):
                from apps.properties.access import get_accessible_property_ids
                prop_ids = get_accessible_property_ids(user)
                qs = qs.filter(unit__property_id__in=prop_ids)

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response(self.get_serializer(qs, many=True).data)

    # --- Dispatch & Quoting ---

    @action(detail=True, methods=["get", "post"], url_path="dispatch")
    def job_dispatch(self, request, pk=None):
        mreq = self.get_object()

        if request.method == "GET":
            try:
                d = mreq.dispatch
                return Response(JobDispatchSerializer(d).data)
            except JobDispatch.DoesNotExist:
                return Response({"detail": "No dispatch yet"}, status=status.HTTP_404_NOT_FOUND)

        # POST — create dispatch + rank suppliers (inherit agency from request)
        jd, created = JobDispatch.objects.get_or_create(
            maintenance_request=mreq,
            defaults={"dispatched_by": request.user, "agency_id": mreq.agency_id},
        )
        suggestions = rank_suppliers(mreq)
        return Response({
            "dispatch": JobDispatchSerializer(jd).data,
            "suggestions": suggestions,
        })

    @action(detail=True, methods=["post"], url_path="dispatch/send")
    def dispatch_send(self, request, pk=None):
        mreq = self.get_object()
        try:
            jd = mreq.dispatch
        except JobDispatch.DoesNotExist:
            return Response({"detail": "Create dispatch first"}, status=status.HTTP_400_BAD_REQUEST)

        supplier_ids = request.data.get("supplier_ids", [])
        notes = request.data.get("notes", "")

        if not supplier_ids:
            return Response({"detail": "supplier_ids required"}, status=status.HTTP_400_BAD_REQUEST)

        if notes:
            jd.notes = notes

        jd.status = JobDispatch.Status.SENT
        jd.dispatched_at = timezone.now()
        jd.save()

        sent = 0
        for sid in supplier_ids:
            supplier = Supplier.objects.filter(id=sid, is_active=True).first()
            if not supplier:
                continue
            qr, created = JobQuoteRequest.objects.get_or_create(
                dispatch=jd, supplier=supplier,
                defaults={"agency_id": jd.agency_id},
            )
            if created or not qr.notified_at:
                notify_supplier(qr)
                qr.notified_at = timezone.now()
                qr.save()
                sent += 1

        return Response({
            "sent": sent,
            "dispatch": JobDispatchSerializer(jd).data,
        })

    @action(
        detail=True, methods=["get", "post"], url_path="activity",
        parser_classes=[JSONParser, MultiPartParser, FormParser],
    )
    def activity(self, request, pk=None):
        mreq = self.get_object()
        if request.method == "GET":
            # Always sync from linked chat session — dedup inside
            # persist_chat_history_to_request prevents duplicates, so this
            # is safe to call on every load. This ensures the admin always
            # sees the full tenant conversation history when opening a ticket.
            linked_session = mreq.tenant_chat_sessions.order_by("-updated_at").first()
            if linked_session and linked_session.messages:
                persist_chat_history_to_request(
                    mreq,
                    linked_session.messages,
                    created_by=linked_session.user,
                    session_id=linked_session.pk,
                    source="tenant_chat",
                )
            activities = mreq.activities.select_related("created_by").all()
            return Response(MaintenanceActivitySerializer(activities, many=True).data)

        serializer = MaintenanceActivitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(request=mreq, created_by=request.user, agency_id=mreq.agency_id)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="dispatch/award")
    def dispatch_award(self, request, pk=None):
        mreq = self.get_object()
        quote_request_id = request.data.get("quote_request_id")
        if not quote_request_id:
            return Response({"detail": "quote_request_id required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            jd = mreq.dispatch
        except JobDispatch.DoesNotExist:
            return Response({"detail": "No dispatch"}, status=status.HTTP_400_BAD_REQUEST)

        qr = jd.quote_requests.filter(id=quote_request_id).first()
        if not qr:
            return Response({"detail": "Quote request not found"}, status=status.HTTP_404_NOT_FOUND)

        # Award this supplier
        qr.status = JobQuoteRequest.Status.AWARDED
        qr.save()

        # Decline others
        jd.quote_requests.exclude(id=qr.id).update(status=JobQuoteRequest.Status.EXPIRED)

        # Update dispatch and maintenance request
        jd.status = JobDispatch.Status.AWARDED
        jd.save()
        mreq.supplier = qr.supplier
        mreq.status = MaintenanceRequest.Status.IN_PROGRESS
        mreq.save()

        # Create SupplierJobAssignment for portal access (POPIA data-minimised snapshot).
        # Only possible when the supplier has a linked user account.
        from .models import SupplierJobAssignment
        awarded_supplier = qr.supplier
        if awarded_supplier.linked_user_id:
            prop = mreq.unit.property
            # Build a plain address string from whatever address data exists.
            addr_parts = [prop.address]
            if prop.city:
                addr_parts.append(prop.city)
            if prop.province:
                addr_parts.append(prop.province)
            property_address = ", ".join(filter(None, addr_parts)) or "Address not provided"

            tenant_name = ""
            tenant_phone = ""
            if mreq.tenant:
                tenant_name = mreq.tenant.get_full_name() or mreq.tenant.email
                tenant_phone = getattr(mreq.tenant, "phone", "") or ""

            SupplierJobAssignment.objects.get_or_create(
                supplier=awarded_supplier.linked_user,
                maintenance_request=mreq,
                defaults={
                    "property_address": property_address,
                    "tenant_contact_name": tenant_name,
                    "tenant_contact_phone": tenant_phone,
                    "scope_of_work": mreq.description or mreq.title,
                    "assigned_by": request.user,
                    "agency_id": mreq.agency_id,
                },
            )

        return Response(JobDispatchSerializer(jd).data)


class JobDispatchListView(APIView):
    """List all active dispatches for the dispatch overview."""
    permission_classes = [IsAgentOrAdmin]

    def get(self, request):
        from apps.properties.access import get_accessible_property_ids
        prop_ids = get_accessible_property_ids(request.user)
        qs = JobDispatch.objects.all()
        # Phase 2.5: agency scoping — admin sees all; agency users only their
        # own; orphan users see nothing.
        if not _is_admin(request.user):
            agency_id = getattr(request.user, "agency_id", None)
            if agency_id is None:
                qs = qs.none()
            else:
                qs = qs.filter(agency_id=agency_id)
        dispatches = qs.filter(
            maintenance_request__unit__property_id__in=prop_ids
        ).select_related(
            "maintenance_request__unit__property", "dispatched_by"
        ).prefetch_related(
            "quote_requests__supplier", "quote_requests__quote"
        ).exclude(status="cancelled").order_by("-created_at")

        return Response(JobDispatchSerializer(dispatches, many=True).data)


# --- Supplier-facing quote views (token-based, no auth) ---

class SupplierQuoteView(APIView):
    """Token-based view for suppliers to view job and submit quotes."""
    permission_classes = [AllowAny]

    def get(self, request, token):
        qr = get_object_or_404(
            JobQuoteRequest.objects.select_related(
                "dispatch__maintenance_request__unit__property",
                "supplier",
            ),
            token=token,
        )
        # Mark as viewed
        if not qr.viewed_at:
            qr.viewed_at = timezone.now()
            if qr.status == JobQuoteRequest.Status.PENDING:
                qr.status = JobQuoteRequest.Status.VIEWED
            qr.save()

        return Response(SupplierQuotePageSerializer(qr).data)

    def post(self, request, token):
        qr = get_object_or_404(JobQuoteRequest, token=token)

        if qr.status in (JobQuoteRequest.Status.AWARDED, JobQuoteRequest.Status.EXPIRED):
            return Response({"detail": "This quote request is closed"}, status=status.HTTP_400_BAD_REQUEST)

        if hasattr(qr, "quote"):
            return Response({"detail": "Quote already submitted"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = JobQuoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(quote_request=qr, agency_id=qr.agency_id)

        qr.status = JobQuoteRequest.Status.QUOTED
        qr.save()

        # Update dispatch to quoting if first quote
        dispatch = qr.dispatch
        if dispatch.status == JobDispatch.Status.SENT:
            dispatch.status = JobDispatch.Status.QUOTING
            dispatch.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SupplierQuoteDeclineView(APIView):
    """Token-based view for suppliers to decline a job."""
    permission_classes = [AllowAny]

    def post(self, request, token):
        qr = get_object_or_404(JobQuoteRequest, token=token)
        if qr.status in (JobQuoteRequest.Status.AWARDED, JobQuoteRequest.Status.EXPIRED):
            return Response({"detail": "This quote request is closed"}, status=status.HTTP_400_BAD_REQUEST)

        qr.status = JobQuoteRequest.Status.DECLINED
        qr.save()
        return Response({"status": "declined"})


class SupplierViewSet(AgencyScopedQuerysetMixin, AgencyStampedCreateMixin, viewsets.ModelViewSet):
    permission_classes = [IsAgentOrAdmin]
    filterset_fields = ["is_active"]
    queryset = Supplier.objects.all()

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("trades", "documents", "property_links__property").annotate(
            active_jobs_count=Count(
                "assigned_requests",
                filter=Q(assigned_requests__status__in=["open", "in_progress"]),
            ),
            document_count=Count("documents"),
            property_count=Count("property_links"),
            has_bank_confirmation=Exists(
                SupplierDocument.objects.filter(
                    supplier=OuterRef("pk"),
                    document_type="bank_confirmation",
                )
            ),
        )
        prop_id = self.request.query_params.get("property")
        if prop_id:
            qs = qs.filter(property_links__property_id=prop_id)
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return SupplierListSerializer
        return SupplierSerializer

    @action(detail=True, methods=["get"])
    def requests(self, request, pk=None):
        supplier = self.get_object()
        qs = supplier.assigned_requests.select_related("unit__property").all()
        data = MaintenanceRequestSerializer(qs, many=True).data
        return Response(data)

    # --- Document management ---

    @action(detail=True, methods=["get", "post"], parser_classes=[MultiPartParser, FormParser])
    def documents(self, request, pk=None):
        supplier = self.get_object()
        if request.method == "GET":
            docs = supplier.documents.all()
            return Response(SupplierDocumentSerializer(docs, many=True).data)

        serializer = SupplierDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(supplier=supplier, agency_id=supplier.agency_id)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path="documents/(?P<doc_id>[0-9]+)")
    def delete_document(self, request, pk=None, doc_id=None):
        supplier = self.get_object()
        doc = supplier.documents.filter(id=doc_id).first()
        if not doc:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        doc.file.delete(save=False)
        doc.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # --- Property linking ---

    @action(detail=True, methods=["get", "post"])
    def properties(self, request, pk=None):
        supplier = self.get_object()
        if request.method == "GET":
            links = supplier.property_links.select_related("property").all()
            return Response(SupplierPropertySerializer(links, many=True).data)

        serializer = SupplierPropertySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(supplier=supplier, agency_id=supplier.agency_id)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path="properties/(?P<link_id>[0-9]+)")
    def remove_property(self, request, pk=None, link_id=None):
        supplier = self.get_object()
        link = supplier.property_links.filter(id=link_id).first()
        if not link:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        link.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def attach_group(self, request, pk=None):
        """Attach all properties from a PropertyGroup to this supplier."""
        from apps.properties.models import PropertyGroup
        supplier = self.get_object()
        group_id = request.data.get("group_id")
        if not group_id:
            return Response({"detail": "group_id required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            group = PropertyGroup.objects.get(id=group_id)
        except PropertyGroup.DoesNotExist:
            return Response({"detail": "Group not found"}, status=status.HTTP_404_NOT_FOUND)

        created = 0
        for prop in group.properties.all():
            _, was_created = SupplierProperty.objects.get_or_create(
                supplier=supplier, property=prop,
                defaults={"agency_id": supplier.agency_id},
            )
            if was_created:
                created += 1

        return Response({"attached": created})

    # --- Excel import ---

    @action(detail=False, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def import_excel(self, request):
        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"detail": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            import openpyxl
        except ImportError:
            return Response(
                {"detail": "openpyxl not installed on server"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            wb = openpyxl.load_workbook(uploaded, read_only=True)
            ws = wb.active
        except Exception:
            return Response({"detail": "Invalid Excel file"}, status=status.HTTP_400_BAD_REQUEST)

        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return Response({"detail": "Empty file"}, status=status.HTTP_400_BAD_REQUEST)

        # Normalise headers
        headers = [str(h).strip().lower().replace(" ", "_") if h else "" for h in rows[0]]

        col_map = {
            "company_name": "company_name",
            "company": "company_name",
            "contact_person": "name",
            "contact": "name",
            "name": "name",
            "phone": "phone",
            "email": "email",
            "website": "website",
            "address": "address",
            "city": "city",
            "province": "province",
            "trades": "_trades",
            "services": "_trades",
        }

        created = 0
        errors = []

        for row_idx, row in enumerate(rows[1:], start=2):
            data = {}
            trades_raw = ""
            for col_idx, value in enumerate(row):
                if col_idx >= len(headers):
                    break
                header = headers[col_idx]
                field = col_map.get(header)
                if field == "_trades":
                    trades_raw = str(value or "")
                elif field:
                    data[field] = str(value or "").strip()

            if not data.get("name") and not data.get("company_name"):
                continue  # skip empty rows

            if not data.get("phone"):
                errors.append(f"Row {row_idx}: missing phone")
                continue

            if not data.get("name"):
                data["name"] = data.get("company_name", "")

            try:
                # Stamp the caller's agency so imported suppliers stay scoped.
                agency_id = getattr(request.user, "agency_id", None)
                supplier = Supplier.objects.create(agency_id=agency_id, **data)
                if trades_raw:
                    valid_trades = {c[0] for c in Supplier.Trade.choices}
                    for t in trades_raw.split(","):
                        t = t.strip().lower().replace(" ", "_")
                        if t in valid_trades:
                            SupplierTrade.objects.get_or_create(
                                supplier=supplier, trade=t,
                                defaults={"agency_id": agency_id},
                            )
                created += 1
            except Exception as e:
                errors.append(f"Row {row_idx}: {str(e)[:100]}")

        return Response({"created": created, "errors": errors})


class AgentQuestionViewSet(AgencyScopedQuerysetMixin, AgencyStampedCreateMixin, viewsets.ModelViewSet):
    serializer_class = AgentQuestionSerializer
    permission_classes = [IsAgentOrAdmin]
    queryset = AgentQuestion.objects.all()

    def get_queryset(self):
        qs = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        category = self.request.query_params.get('category')
        if status_filter:
            qs = qs.filter(status=status_filter)
        if category:
            qs = qs.filter(category=category)
        return qs

    @action(detail=True, methods=['post'])
    def answer(self, request, pk=None):
        question = self.get_object()
        answer_text = request.data.get('answer', '').strip()
        if not answer_text:
            return Response({'error': 'Answer is required.'}, status=status.HTTP_400_BAD_REQUEST)
        question.answer = answer_text
        question.status = AgentQuestion.Status.ANSWERED
        question.answered_by = request.user
        question.answered_at = timezone.now()
        question.added_to_context = True
        question.save()
        return Response(AgentQuestionSerializer(question).data)

    @action(detail=True, methods=['post'])
    def dismiss(self, request, pk=None):
        question = self.get_object()
        question.status = AgentQuestion.Status.DISMISSED
        question.save()
        return Response(AgentQuestionSerializer(question).data)


class MaintenanceSkillViewSet(AgencyStampedCreateMixin, viewsets.ModelViewSet):
    serializer_class = MaintenanceSkillSerializer
    permission_classes = [IsAgentOrAdmin]
    filterset_fields = ["trade", "difficulty", "is_active"]
    pagination_class = None  # small catalog — return all rows for admin / agent UI
    queryset = MaintenanceSkill.objects.all()

    def get_queryset(self):
        # MaintenanceSkill.agency is nullable; null = platform-global library
        # entry visible to every tenant. Agency users see global + own; admin
        # sees everything.
        user = self.request.user
        qs = MaintenanceSkill.objects.all()
        if not _is_admin(user):
            agency_id = getattr(user, "agency_id", None)
            if agency_id is None:
                qs = qs.filter(agency__isnull=True)
            else:
                qs = qs.filter(Q(agency_id=agency_id) | Q(agency__isnull=True))
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(notes__icontains=search))
        return qs


class AgentInvoiceApprovalView(APIView):
    """
    Agent reviews a supplier invoice: approve / reject / mark as paid.

    GET  /maintenance/<request_pk>/invoice/
         Returns the invoice for the maintenance request (404 if none).

    POST /maintenance/<request_pk>/invoice/
         Single-endpoint pattern — body: { "action": "approve"|"reject"|"paid",
         "reason": "<str>",      # required when action="reject"
         "reference": "<str>" }  # optional EFT ref when action="paid"
    """

    permission_classes = [IsAgentOrAdmin]

    def _get_invoice(self, request_pk, request=None):
        try:
            qs = SupplierInvoice.objects.select_related(
                "quote_request__dispatch__maintenance_request",
                "quote_request__supplier",
            )
            # Phase 2.5: enforce agency scoping — non-admin users can only
            # access invoices in their own agency.
            if request is not None and not _is_admin(request.user):
                agency_id = getattr(request.user, "agency_id", None)
                if agency_id is None:
                    return None
                qs = qs.filter(agency_id=agency_id)
            return qs.get(quote_request__dispatch__maintenance_request_id=request_pk)
        except SupplierInvoice.DoesNotExist:
            return None

    def get(self, request, request_pk):
        invoice = self._get_invoice(request_pk, request=request)
        if not invoice:
            return Response({"detail": "No invoice found for this job"}, status=status.HTTP_404_NOT_FOUND)
        from .supplier_serializers import SupplierInvoiceSerializer
        return Response(SupplierInvoiceSerializer(invoice).data)

    def post(self, request, request_pk):
        action_name = request.data.get("action")
        invoice = self._get_invoice(request_pk, request=request)
        if not invoice:
            return Response({"detail": "No invoice found for this job"}, status=status.HTTP_404_NOT_FOUND)

        if action_name == "approve":
            if invoice.status not in ("pending",):
                return Response({"detail": "Only pending invoices can be approved"}, status=status.HTTP_400_BAD_REQUEST)
            invoice.status = SupplierInvoice.Status.APPROVED
            invoice.reviewed_by = request.user
            invoice.save(update_fields=["status", "reviewed_by", "updated_at"])
            MaintenanceActivity.objects.create(
                request=invoice.quote_request.dispatch.maintenance_request,
                activity_type=MaintenanceActivity.ActivityType.NOTE,
                message=f"Invoice of R{invoice.total_amount} approved by agent.",
                created_by=request.user,
                metadata={"invoice_id": invoice.id},
                agency_id=invoice.agency_id,
            )
            return Response({"status": "approved"})

        elif action_name == "reject":
            if invoice.status != SupplierInvoice.Status.PENDING:
                return Response({"detail": "Only pending invoices can be rejected"}, status=status.HTTP_400_BAD_REQUEST)
            reason = request.data.get("reason", "").strip()
            if not reason:
                return Response({"detail": "rejection reason required"}, status=status.HTTP_400_BAD_REQUEST)
            invoice.status = SupplierInvoice.Status.REJECTED
            invoice.rejection_reason = reason
            invoice.reviewed_by = request.user
            invoice.save(update_fields=["status", "rejection_reason", "reviewed_by", "updated_at"])
            MaintenanceActivity.objects.create(
                request=invoice.quote_request.dispatch.maintenance_request,
                activity_type=MaintenanceActivity.ActivityType.NOTE,
                message=f"Invoice rejected: {reason}",
                created_by=request.user,
                metadata={"invoice_id": invoice.id},
                agency_id=invoice.agency_id,
            )
            return Response({"status": "rejected"})

        elif action_name == "paid":
            if invoice.status != "approved":
                return Response({"detail": "Only approved invoices can be marked paid"}, status=status.HTTP_400_BAD_REQUEST)
            reference = request.data.get("reference", "").strip()
            invoice.status = SupplierInvoice.Status.PAID
            invoice.paid_at = timezone.now()
            invoice.paid_reference = reference
            invoice.reviewed_by = request.user
            invoice.save(update_fields=["status", "paid_at", "paid_reference", "reviewed_by", "updated_at"])
            MaintenanceActivity.objects.create(
                request=invoice.quote_request.dispatch.maintenance_request,
                activity_type=MaintenanceActivity.ActivityType.NOTE,
                message=f"Invoice paid (R{invoice.total_amount}). Reference: {reference or 'not provided'}.",
                created_by=request.user,
                metadata={"invoice_id": invoice.id},
                agency_id=invoice.agency_id,
            )
            return Response({"status": "paid"})

        return Response({"detail": "action must be one of: approve, reject, paid"}, status=status.HTTP_400_BAD_REQUEST)
