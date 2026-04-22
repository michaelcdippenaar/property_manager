"""DRF serializers for the payments app."""

from decimal import Decimal

from rest_framework import serializers

from .models import PaymentAuditLog, RentInvoice, RentPayment, UnmatchedPayment


class RentPaymentSerializer(serializers.ModelSerializer):
    actor_email = serializers.SerializerMethodField()

    class Meta:
        model = RentPayment
        fields = [
            "id",
            "invoice",
            "amount",
            "payment_date",
            "reference",
            "payer_name",
            "source",
            "status",
            "reversed_at",
            "reversal_reason",
            "created_at",
            "actor_email",
        ]
        read_only_fields = ["id", "status", "reversed_at", "reversal_reason", "created_at"]

    def get_actor_email(self, obj):
        return getattr(obj.created_by, "email", None)


class RentInvoiceSerializer(serializers.ModelSerializer):
    payments = RentPaymentSerializer(many=True, read_only=True)
    amount_paid = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    balance_remaining = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    tenant_in_credit = serializers.BooleanField(read_only=True)
    lease_number = serializers.SerializerMethodField()

    class Meta:
        model = RentInvoice
        fields = [
            "id",
            "lease",
            "lease_number",
            "period_start",
            "period_end",
            "amount_due",
            "credit_balance",
            "status",
            "due_date",
            "amount_paid",
            "balance_remaining",
            "tenant_in_credit",
            "payments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]

    def get_lease_number(self, obj):
        return getattr(obj.lease, "lease_number", None) or str(obj.lease_id)


class UnmatchedPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnmatchedPayment
        fields = [
            "id",
            "amount",
            "payment_date",
            "reference",
            "payer_name",
            "bank_statement_line",
            "status",
            "assigned_to_invoice",
            "resolved_payment",
            "resolved_at",
            "notes",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "assigned_to_invoice",
            "resolved_payment",
            "resolved_at",
            "created_at",
        ]


class PaymentAuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.SerializerMethodField()

    class Meta:
        model = PaymentAuditLog
        fields = [
            "id",
            "entity_type",
            "entity_id",
            "lease_id",
            "event",
            "from_status",
            "to_status",
            "detail",
            "actor_email",
            "created_at",
        ]

    def get_actor_email(self, obj):
        return getattr(obj.actor, "email", None)


# Input-only serializers used by action endpoints

class RecordPaymentInputSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0.01"))
    payment_date = serializers.DateField()
    source = serializers.ChoiceField(
        choices=[("tenant", "Tenant"), ("guarantor", "Guarantor"), ("other", "Other")],
        default="tenant",
    )
    payer_name = serializers.CharField(max_length=200, allow_blank=True, default="")
    reference = serializers.CharField(max_length=150, allow_blank=True, default="")


class ReversePaymentInputSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=1, max_length=500)


class AssignUnmatchedInputSerializer(serializers.Serializer):
    invoice_id = serializers.IntegerField()
    source = serializers.ChoiceField(
        choices=[("tenant", "Tenant"), ("guarantor", "Guarantor"), ("other", "Other")],
        default="tenant",
    )
    payer_name = serializers.CharField(max_length=200, allow_blank=True, default="")
