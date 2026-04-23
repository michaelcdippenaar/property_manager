from rest_framework import serializers
from .models import (
    JobQuote, JobQuoteRequest, Supplier, SupplierDocument, SupplierInvoice, SupplierTrade,
)


class SupplierTradeSerializer(serializers.ModelSerializer):
    label = serializers.CharField(source="get_trade_display", read_only=True)

    class Meta:
        model = SupplierTrade
        fields = ["id", "trade", "label"]


class SupplierDocumentSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source="get_document_type_display", read_only=True)

    class Meta:
        model = SupplierDocument
        fields = ["id", "document_type", "type_label", "file", "description", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]


class SupplierProfileSerializer(serializers.ModelSerializer):
    trades = SupplierTradeSerializer(many=True, read_only=True)
    documents = SupplierDocumentSerializer(many=True, read_only=True)
    trade_codes = serializers.ListField(
        child=serializers.ChoiceField(choices=Supplier.Trade.choices),
        write_only=True, required=False,
    )

    class Meta:
        model = Supplier
        exclude = ["ai_profile", "linked_user"]
        read_only_fields = ["created_at", "updated_at", "rating"]

    def update(self, instance, validated_data):
        trade_codes = validated_data.pop("trade_codes", None)
        supplier = super().update(instance, validated_data)
        if trade_codes is not None:
            supplier.trades.all().delete()
            for code in trade_codes:
                SupplierTrade.objects.get_or_create(supplier=supplier, trade=code)
        return supplier


class SupplierJobQuoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobQuote
        fields = ["id", "amount", "description", "estimated_days", "available_from", "submitted_at"]
        read_only_fields = ["id", "submitted_at"]


class SupplierJobSerializer(serializers.ModelSerializer):
    """A job (quote request) as seen by the supplier."""
    job_title = serializers.CharField(source="dispatch.maintenance_request.title", read_only=True)
    job_description = serializers.CharField(source="dispatch.maintenance_request.description", read_only=True)
    job_priority = serializers.CharField(source="dispatch.maintenance_request.priority", read_only=True)
    mr_status = serializers.CharField(source="dispatch.maintenance_request.status", read_only=True)
    property_city = serializers.SerializerMethodField()
    property_name = serializers.SerializerMethodField()
    dispatch_notes = serializers.CharField(source="dispatch.notes", read_only=True)
    quote = SupplierJobQuoteSerializer(read_only=True)
    invoice_status = serializers.SerializerMethodField()

    class Meta:
        model = JobQuoteRequest
        fields = [
            "id", "status", "mr_status", "job_title", "job_description", "job_priority",
            "property_city", "property_name", "dispatch_notes",
            "match_score", "notified_at", "viewed_at", "quote", "invoice_status", "created_at",
        ]

    def get_property_city(self, obj):
        try:
            return obj.dispatch.maintenance_request.unit.property.city
        except AttributeError:
            return ""

    def get_property_name(self, obj):
        try:
            return obj.dispatch.maintenance_request.unit.property.name
        except AttributeError:
            return ""

    def get_invoice_status(self, obj):
        try:
            return obj.invoice.status
        except Exception:
            return None


class SupplierCalendarItemSerializer(serializers.Serializer):
    """Awarded jobs formatted for calendar display."""
    id = serializers.IntegerField(source="quote_request_id")
    title = serializers.CharField()
    property_name = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    status = serializers.CharField()


class SupplierInvoiceSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    job_title = serializers.SerializerMethodField()

    class Meta:
        model = SupplierInvoice
        fields = [
            "id", "status", "status_label", "job_title",
            "invoice_file", "line_items", "total_amount", "notes",
            "rejection_reason", "paid_at", "paid_reference",
            "submitted_at", "updated_at",
        ]
        read_only_fields = ["id", "status", "rejection_reason", "paid_at", "paid_reference", "submitted_at", "updated_at"]

    def get_job_title(self, obj):
        try:
            return obj.quote_request.dispatch.maintenance_request.title
        except AttributeError:
            return ""


_INVOICE_FILE_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_ALLOWED_INVOICE_MIME_TYPES = {"application/pdf"}
_ALLOWED_IMAGE_MIME_PREFIXES = ("image/",)


def _validate_file(uploaded_file, allow_pdf: bool = True, allow_images: bool = True, max_bytes: int = _INVOICE_FILE_MAX_BYTES):
    """
    Shared validator for supplier file uploads.
    Raises ValidationError if the MIME type or size is not acceptable.
    """
    if uploaded_file is None:
        return uploaded_file

    mime = getattr(uploaded_file, "content_type", "") or ""
    allowed = False
    if allow_pdf and mime in _ALLOWED_INVOICE_MIME_TYPES:
        allowed = True
    if allow_images and any(mime.startswith(prefix) for prefix in _ALLOWED_IMAGE_MIME_PREFIXES):
        allowed = True

    if not allowed:
        raise serializers.ValidationError(
            "Only PDF and image files are accepted. Received: {}".format(mime or "unknown")
        )

    if uploaded_file.size > max_bytes:
        mb = max_bytes // (1024 * 1024)
        raise serializers.ValidationError(
            "File too large. Maximum allowed size is {} MB.".format(mb)
        )

    return uploaded_file


class SupplierInvoiceSubmitSerializer(serializers.ModelSerializer):
    """Writable serializer for supplier submitting an invoice."""

    class Meta:
        model = SupplierInvoice
        fields = ["invoice_file", "line_items", "total_amount", "notes"]

    def validate_invoice_file(self, value):
        return _validate_file(value, allow_pdf=True, allow_images=True)
