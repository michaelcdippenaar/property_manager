from rest_framework import serializers
from apps.maintenance.chat_history import persist_chat_history_to_request
from .models import (
    AgentQuestion, JobDispatch, JobQuote, JobQuoteRequest,
    MaintenanceActivity, MaintenanceRequest, MaintenanceSkill, Supplier, SupplierTrade,
    SupplierDocument, SupplierProperty,
)


class SupplierTradeSerializer(serializers.ModelSerializer):
    label = serializers.CharField(source="get_trade_display", read_only=True)

    class Meta:
        model = SupplierTrade
        fields = ["id", "trade", "label"]
        read_only_fields = ["id"]


class SupplierDocumentSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source="get_document_type_display", read_only=True)

    class Meta:
        model = SupplierDocument
        fields = ["id", "document_type", "type_label", "file", "description", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]


class SupplierPropertySerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)
    property_city = serializers.CharField(source="property.city", read_only=True)
    property_type = serializers.CharField(source="property.property_type", read_only=True)

    class Meta:
        model = SupplierProperty
        fields = [
            "id", "property", "property_name", "property_city", "property_type",
            "is_preferred", "notes", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class SupplierListSerializer(serializers.ModelSerializer):
    trades = SupplierTradeSerializer(many=True, read_only=True)
    active_jobs_count = serializers.IntegerField(read_only=True, default=0)
    display_name = serializers.CharField(read_only=True)
    document_count = serializers.IntegerField(read_only=True, default=0)
    property_count = serializers.IntegerField(read_only=True, default=0)
    has_bank_confirmation = serializers.BooleanField(read_only=True, default=False)

    class Meta:
        model = Supplier
        fields = [
            "id", "name", "company_name", "display_name", "phone", "email",
            "website", "city", "province", "latitude", "longitude",
            "is_active", "rating", "trades",
            "active_jobs_count", "document_count", "property_count",
            "has_bank_confirmation", "created_at",
        ]


class SupplierSerializer(serializers.ModelSerializer):
    trades = SupplierTradeSerializer(many=True, read_only=True)
    trade_codes = serializers.ListField(
        child=serializers.ChoiceField(choices=Supplier.Trade.choices),
        write_only=True, required=False,
    )
    documents = SupplierDocumentSerializer(many=True, read_only=True)
    property_links = SupplierPropertySerializer(many=True, read_only=True)
    active_jobs_count = serializers.IntegerField(read_only=True, default=0)
    display_name = serializers.CharField(read_only=True)
    document_count = serializers.IntegerField(read_only=True, default=0)
    property_count = serializers.IntegerField(read_only=True, default=0)
    has_bank_confirmation = serializers.BooleanField(read_only=True, default=False)

    class Meta:
        model = Supplier
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]

    def create(self, validated_data):
        trade_codes = validated_data.pop("trade_codes", [])
        supplier = super().create(validated_data)
        for code in trade_codes:
            SupplierTrade.objects.create(supplier=supplier, trade=code)
        return supplier

    def update(self, instance, validated_data):
        trade_codes = validated_data.pop("trade_codes", None)
        supplier = super().update(instance, validated_data)
        if trade_codes is not None:
            supplier.trades.all().delete()
            for code in trade_codes:
                SupplierTrade.objects.create(supplier=supplier, trade=code)
        return supplier


class MaintenanceRequestSerializer(serializers.ModelSerializer):
    initial_chat_history = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False,
        default=list,
    )
    conversation_id = serializers.IntegerField(
        write_only=True,
        required=False,
        default=None,
        help_text="TenantChatSession PK — links the chat to this request and persists messages.",
    )
    supplier_name = serializers.CharField(
        source="supplier.display_name", read_only=True, default=None,
    )
    tenant_name = serializers.CharField(
        source="tenant.full_name", read_only=True, default=None,
    )
    activity_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = MaintenanceRequest
        fields = "__all__"
        read_only_fields = ["tenant", "created_at", "updated_at"]
        extra_kwargs = {
            "unit": {"required": False},
        }

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["tenant"] = user
        initial_chat_history = validated_data.pop("initial_chat_history", [])
        conversation_id = validated_data.pop("conversation_id", None)

        # Auto-assign unit for tenant users who don't specify one
        if "unit" not in validated_data:
            unit = self._resolve_tenant_unit(user)
            if unit is None:
                raise serializers.ValidationError({"unit": "Could not determine your unit. Please contact management."})
            validated_data["unit"] = unit

        # ── RAG-based classification: suggest category/priority from past issues ──
        self._apply_rag_classification(validated_data)

        request_obj = super().create(validated_data)

        # Link the chat session to the new maintenance request and persist messages.
        # Wrapped in try/except so post-creation failures don't return a 500
        # while the record is already committed (causes "error but still created").
        try:
            if conversation_id:
                self._link_chat_session(request_obj, user, conversation_id)
            elif initial_chat_history:
                persist_chat_history_to_request(
                    request_obj,
                    initial_chat_history,
                    created_by=user,
                    source="maintenance_create_api",
                )
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                "Post-creation step failed for maintenance request #%s", request_obj.pk
            )
        return request_obj

    def _link_chat_session(self, request_obj, user, conversation_id):
        """Link a TenantChatSession to this maintenance request and persist its messages."""
        from apps.ai.models import TenantChatSession
        try:
            session = TenantChatSession.objects.get(pk=conversation_id, user=user)
        except TenantChatSession.DoesNotExist:
            return  # silently skip — don't block ticket creation

        # Set the bidirectional link
        if not session.maintenance_request_id:
            TenantChatSession.objects.filter(pk=session.pk).update(
                maintenance_request_id=request_obj.id
            )

        # Persist all chat messages to the maintenance request activity feed
        messages = session.messages or []
        if messages:
            persist_chat_history_to_request(
                request_obj,
                messages,
                created_by=user,
                session_id=session.pk,
                source="tenant_chat",
            )

    def _resolve_tenant_unit(self, user):
        """Find the tenant's unit from their most recent maintenance request or lease."""
        # 1. Most recent maintenance request for this tenant
        prev = MaintenanceRequest.objects.filter(tenant=user).order_by("-created_at").values_list("unit_id", flat=True).first()
        if prev:
            from apps.properties.models import Unit
            return Unit.objects.filter(id=prev).first()

        # 2. Active lease (via Person → Lease → Unit)
        try:
            from apps.leases.models import Lease
            from apps.accounts.models import Person
            person = Person.objects.filter(email=user.email).first()
            if person:
                lease = Lease.objects.filter(primary_tenant=person, status="active").order_by("-start_date").first()
                if lease:
                    return lease.unit
        except Exception:
            pass

        # 3. Fallback: first available unit
        from apps.properties.models import Unit
        return Unit.objects.first()

    def _apply_rag_classification(self, validated_data):
        """
        Use RAG similarity (past issues + skill matching) to suggest
        category and priority when the tenant hasn't provided specific ones.

        Only overrides when:
          - category is "other" (default / unset) and RAG has a confident suggestion
          - priority is "medium" (default) and RAG suggests higher severity
        """
        import logging
        logger = logging.getLogger(__name__)

        description = validated_data.get("description", "")
        title = validated_data.get("title", "")
        query = f"{title} {description}".strip()
        if len(query) < 10:
            return  # Too short for meaningful classification

        # Resolve property_id for scoped search
        property_id = None
        unit = validated_data.get("unit")
        if unit and hasattr(unit, "property_id"):
            property_id = unit.property_id

        try:
            from core.contract_rag import classify_from_rag
            classification = classify_from_rag(query, property_id=property_id)
        except Exception as e:
            logger.warning("RAG classification failed during request creation: %s", e)
            return

        # Only apply if confidence is reasonable
        if classification["confidence"] < 0.3:
            return

        current_category = validated_data.get("category", "other")
        current_priority = validated_data.get("priority", "medium")

        # Suggest category when tenant left it as "other" (default)
        if current_category == "other" and classification["category"] != "other":
            validated_data["category"] = classification["category"]
            logger.info(
                "RAG classified category: %s (confidence=%.2f, matches=%d)",
                classification["category"],
                classification["confidence"],
                classification["rag_matches"],
            )

        # Suggest higher priority when RAG indicates severity
        priority_order = {"low": 1, "medium": 2, "high": 3, "urgent": 4}
        rag_pri = classification["priority"]
        if priority_order.get(rag_pri, 0) > priority_order.get(current_priority, 0):
            validated_data["priority"] = rag_pri
            logger.info(
                "RAG bumped priority: %s → %s (confidence=%.2f)",
                current_priority, rag_pri, classification["confidence"],
            )


# --- Dispatch & Quoting ---

class JobQuoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobQuote
        fields = ["id", "amount", "description", "estimated_days", "available_from", "submitted_at"]
        read_only_fields = ["id", "submitted_at"]


class JobQuoteRequestSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.display_name", read_only=True)
    supplier_phone = serializers.CharField(source="supplier.phone", read_only=True)
    supplier_city = serializers.CharField(source="supplier.city", read_only=True)
    quote = JobQuoteSerializer(read_only=True)

    class Meta:
        model = JobQuoteRequest
        fields = [
            "id", "supplier", "supplier_name", "supplier_phone", "supplier_city",
            "status", "token", "notified_at", "viewed_at",
            "match_score", "match_reasons", "quote", "created_at",
        ]
        read_only_fields = ["id", "token", "created_at"]


class JobDispatchSerializer(serializers.ModelSerializer):
    quote_requests = JobQuoteRequestSerializer(many=True, read_only=True)
    dispatched_by_name = serializers.CharField(source="dispatched_by.full_name", read_only=True, default=None)
    request_title = serializers.CharField(source="maintenance_request.title", read_only=True)
    request_priority = serializers.CharField(source="maintenance_request.priority", read_only=True)

    class Meta:
        model = JobDispatch
        fields = [
            "id", "maintenance_request", "request_title", "request_priority",
            "status", "dispatched_by", "dispatched_by_name", "dispatched_at",
            "notes", "quote_requests", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SupplierQuotePageSerializer(serializers.ModelSerializer):
    """Serializer for the supplier-facing quote page — no sensitive data."""
    job_title = serializers.CharField(source="dispatch.maintenance_request.title", read_only=True)
    job_description = serializers.CharField(source="dispatch.maintenance_request.description", read_only=True)
    job_priority = serializers.CharField(source="dispatch.maintenance_request.priority", read_only=True)
    property_city = serializers.SerializerMethodField()
    dispatch_notes = serializers.CharField(source="dispatch.notes", read_only=True)
    quote = JobQuoteSerializer(read_only=True)

    class Meta:
        model = JobQuoteRequest
        fields = [
            "id", "status", "job_title", "job_description", "job_priority",
            "property_city", "dispatch_notes", "quote",
        ]

    def get_property_city(self, obj):
        try:
            return obj.dispatch.maintenance_request.unit.property.city
        except AttributeError:
            return ""


class AgentQuestionSerializer(serializers.ModelSerializer):
    answered_by_name = serializers.CharField(source='answered_by.full_name', read_only=True, default='')
    property_name = serializers.CharField(source='property.name', read_only=True, default='')

    class Meta:
        model = AgentQuestion
        fields = [
            'id', 'question', 'answer', 'category', 'status',
            'context_source', 'property', 'property_name',
            'answered_by', 'answered_by_name', 'answered_at',
            'added_to_context', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'answered_by', 'answered_at', 'added_to_context', 'created_at', 'updated_at']


class MaintenanceActivitySerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True, default=None)
    created_by_role = serializers.CharField(source="created_by.role", read_only=True, default=None)
    metadata = serializers.JSONField(required=False, default=dict)

    class Meta:
        model = MaintenanceActivity
        fields = ["id", "activity_type", "message", "file", "metadata", "created_by", "created_by_name", "created_by_role", "created_at"]
        read_only_fields = ["id", "created_by", "created_at"]

    def create(self, validated_data):
        if validated_data.get("metadata") is None:
            validated_data["metadata"] = {}
        return super().create(validated_data)


class MaintenanceSkillSerializer(serializers.ModelSerializer):
    trade_label = serializers.CharField(source="get_trade_display", read_only=True)
    difficulty_label = serializers.CharField(source="get_difficulty_display", read_only=True)

    class Meta:
        model = MaintenanceSkill
        fields = [
            'id', 'name', 'trade', 'trade_label', 'difficulty', 'difficulty_label',
            'symptom_phrases', 'steps', 'notes', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
