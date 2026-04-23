from django.db.models import Count, Exists, OuterRef, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated

from apps.accounts.permissions import IsAgentOrAdmin
from rest_framework.response import Response
from rest_framework.views import APIView

from .matching import rank_suppliers
from .chat_history import persist_chat_history_to_request
from .models import (
    AgentQuestion, JobDispatch, JobQuote, JobQuoteRequest,
    MaintenanceActivity, MaintenanceRequest, MaintenanceSkill, Supplier, SupplierDocument,
    SupplierProperty, SupplierTrade,
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


class MaintenanceRequestViewSet(viewsets.ModelViewSet):
    serializer_class = MaintenanceRequestSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["status", "priority", "unit", "supplier"]

    # Actions that mutate dispatch / awarding state must be agent-only.
    _AGENT_ONLY_ACTIONS = {"dispatch_award", "dispatch_send", "job_dispatch"}

    # Destructive / mutating actions that owner and tenant roles must not perform.
    _WRITE_ACTIONS = {"create", "update", "partial_update", "destroy"}

    def get_permissions(self):
        if self.action in self._AGENT_ONLY_ACTIONS:
            # job_dispatch handles both GET (read) and POST (mutate).
            # Only lock down the mutating POST; GET stays IsAuthenticated.
            if self.action == "job_dispatch" and self.request.method == "GET":
                return [IsAuthenticated()]
            return [IsAgentOrAdmin()]
        if self.action == "destroy":
            # Owners and tenants are read-only; only agents and admins may delete.
            return [IsAgentOrAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        qs = MaintenanceRequest.objects.select_related("supplier", "tenant").annotate(
            activity_count=Count("activities"),
        ).order_by("-created_at")
        if hasattr(user, "role") and user.role == "tenant":
            qs = qs.filter(tenant=user)
        elif hasattr(user, "role") and user.role != "admin":
            from apps.properties.access import get_accessible_property_ids
            prop_ids = get_accessible_property_ids(user)
            qs = qs.filter(unit__property_id__in=prop_ids)
        # admin sees all
        property_id = self.request.query_params.get("property")
        if property_id:
            qs = qs.filter(unit__property_id=property_id)
        exclude_status = self.request.query_params.get("exclude_status")
        if exclude_status:
            qs = qs.exclude(status=exclude_status)
        return qs


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
        """Lightweight counts for sidebar badge indicators."""
        open_issues = MaintenanceRequest.objects.exclude(
            status__in=["closed", "resolved"]
        ).count()
        pending_questions = AgentQuestion.objects.filter(
            status=AgentQuestion.Status.PENDING
        ).count()
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

        # POST — create dispatch + rank suppliers
        jd, created = JobDispatch.objects.get_or_create(
            maintenance_request=mreq,
            defaults={"dispatched_by": request.user},
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
        serializer.save(request=mreq, created_by=request.user)
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
                },
            )

        return Response(JobDispatchSerializer(jd).data)


class JobDispatchListView(APIView):
    """List all active dispatches for the dispatch overview."""
    permission_classes = [IsAgentOrAdmin]

    def get(self, request):
        from apps.properties.access import get_accessible_property_ids
        prop_ids = get_accessible_property_ids(request.user)
        dispatches = JobDispatch.objects.filter(
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
        serializer.save(quote_request=qr)

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


class SupplierViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAgentOrAdmin]
    filterset_fields = ["is_active"]

    def get_queryset(self):
        qs = Supplier.objects.prefetch_related("trades", "documents", "property_links__property").annotate(
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
        serializer.save(supplier=supplier)
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
        serializer.save(supplier=supplier)
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
                supplier = Supplier.objects.create(**data)
                if trades_raw:
                    valid_trades = {c[0] for c in Supplier.Trade.choices}
                    for t in trades_raw.split(","):
                        t = t.strip().lower().replace(" ", "_")
                        if t in valid_trades:
                            SupplierTrade.objects.get_or_create(supplier=supplier, trade=t)
                created += 1
            except Exception as e:
                errors.append(f"Row {row_idx}: {str(e)[:100]}")

        return Response({"created": created, "errors": errors})


class AgentQuestionViewSet(viewsets.ModelViewSet):
    serializer_class = AgentQuestionSerializer
    permission_classes = [IsAgentOrAdmin]

    def get_queryset(self):
        qs = AgentQuestion.objects.all()
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


class MaintenanceSkillViewSet(viewsets.ModelViewSet):
    serializer_class = MaintenanceSkillSerializer
    permission_classes = [IsAgentOrAdmin]
    filterset_fields = ["trade", "difficulty", "is_active"]
    pagination_class = None  # small catalog — return all rows for admin / agent UI

    def get_queryset(self):
        qs = MaintenanceSkill.objects.all()
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(notes__icontains=search))
        return qs
