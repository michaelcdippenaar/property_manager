from rest_framework import serializers
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
    supplier_name = serializers.CharField(
        source="supplier.display_name", read_only=True, default=None,
    )

    class Meta:
        model = MaintenanceRequest
        fields = "__all__"
        read_only_fields = ["tenant", "created_at", "updated_at"]

    def create(self, validated_data):
        validated_data["tenant"] = self.context["request"].user
        return super().create(validated_data)


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

    class Meta:
        model = MaintenanceActivity
        fields = ["id", "activity_type", "message", "metadata", "created_by", "created_by_name", "created_by_role", "created_at"]
        read_only_fields = ["id", "created_by", "created_at"]


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
