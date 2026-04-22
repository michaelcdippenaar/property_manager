from django.utils import timezone
from rest_framework import serializers

from apps.accounts.models import Person
from apps.leases.models import Lease
from apps.properties.models import Unit

from .models import Tenant, TenantOnboarding, TenantUnitAssignment


class TenantPersonSerializer(serializers.ModelSerializer):
    """Lightweight Person projection for tenant context."""

    class Meta:
        model = Person
        fields = ["id", "full_name", "email", "phone", "id_number"]
        read_only_fields = fields


class TenantSerializer(serializers.ModelSerializer):
    person = TenantPersonSerializer(read_only=True)
    person_id = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.all(), source="person", write_only=True,
    )
    current_unit = serializers.SerializerMethodField()
    current_property = serializers.SerializerMethodField()

    class Meta:
        model = Tenant
        fields = [
            "id", "person", "person_id", "linked_user", "is_active",
            "notes", "current_unit", "current_property",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "linked_user", "created_at", "updated_at"]

    def get_current_unit(self, obj: Tenant) -> dict | None:
        a = obj.current_assignment
        if a is None:
            return None
        return {"id": a.unit_id, "unit_number": str(a.unit)}

    def get_current_property(self, obj: Tenant) -> dict | None:
        a = obj.current_assignment
        if a is None:
            return None
        return {"id": a.property_id, "name": str(a.property)}


class TenantUnitAssignmentSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source="tenant.person.full_name", read_only=True)
    tenant_email = serializers.CharField(source="tenant.person.email", read_only=True)
    tenant_phone = serializers.CharField(source="tenant.person.phone", read_only=True)
    unit_number = serializers.CharField(source="unit.unit_number", read_only=True)
    property_name = serializers.CharField(source="property.name", read_only=True)
    source_display = serializers.CharField(source="get_source_display", read_only=True)
    lease_number = serializers.SerializerMethodField()

    class Meta:
        model = TenantUnitAssignment
        fields = [
            "id", "tenant", "tenant_name", "tenant_email", "tenant_phone",
            "unit", "unit_number", "property", "property_name",
            "lease", "lease_number",
            "start_date", "end_date",
            "source", "source_display",
            "assigned_by", "notes", "created_at",
        ]
        read_only_fields = [
            "id", "property", "source", "assigned_by", "created_at",
        ]

    def get_lease_number(self, obj: TenantUnitAssignment) -> str | None:
        if obj.lease:
            return obj.lease.lease_number or f"Lease #{obj.lease_id}"
        return None


class TenantOnboardingSerializer(serializers.ModelSerializer):
    """
    Serializer for TenantOnboarding checklist.

    Read: full state of all checklist items + computed fields.
    Write (PATCH): set any boolean item to true — the serializer automatically
      stamps the corresponding *_at timestamp and updates completed_at when all
      v1 items are ticked.
    """

    progress = serializers.IntegerField(read_only=True)
    is_complete = serializers.BooleanField(read_only=True)
    lease_id = serializers.IntegerField(source="lease_id", read_only=True)
    lease_number = serializers.SerializerMethodField()
    tenant_name = serializers.SerializerMethodField()
    primary_tenant_id = serializers.SerializerMethodField()

    class Meta:
        model = TenantOnboarding
        fields = [
            "id",
            "lease_id",
            "lease_number",
            "tenant_name",
            "primary_tenant_id",
            # v1 items
            "welcome_pack_sent",
            "welcome_pack_sent_at",
            "deposit_received",
            "deposit_received_at",
            "deposit_amount",
            "first_rent_scheduled",
            "first_rent_scheduled_at",
            "keys_handed_over",
            "keys_handed_over_at",
            "emergency_contacts_captured",
            "emergency_contacts_captured_at",
            # v2 deferred
            "incoming_inspection_booked",
            "incoming_inspection_booked_at",
            "deposit_banked_trust",
            "deposit_banked_trust_at",
            # computed
            "progress",
            "is_complete",
            "completed_at",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "lease_id",
            "lease_number",
            "tenant_name",
            "primary_tenant_id",
            "welcome_pack_sent_at",
            "deposit_received_at",
            "first_rent_scheduled_at",
            "keys_handed_over_at",
            "emergency_contacts_captured_at",
            "incoming_inspection_booked_at",
            "deposit_banked_trust_at",
            "progress",
            "is_complete",
            "completed_at",
            "created_at",
            "updated_at",
        ]

    def get_lease_number(self, obj: TenantOnboarding) -> str:
        return obj.lease.lease_number or f"Lease #{obj.lease_id}"

    def get_tenant_name(self, obj: TenantOnboarding) -> str:
        pt = obj.lease.primary_tenant
        return pt.full_name if pt else "—"

    def get_primary_tenant_id(self, obj: TenantOnboarding) -> int | None:
        pt = obj.lease.primary_tenant
        return pt.pk if pt else None

    # Timestamp fields corresponding to each boolean flag
    _TIMESTAMP_MAP: dict[str, str] = {
        "welcome_pack_sent": "welcome_pack_sent_at",
        "deposit_received": "deposit_received_at",
        "first_rent_scheduled": "first_rent_scheduled_at",
        "keys_handed_over": "keys_handed_over_at",
        "emergency_contacts_captured": "emergency_contacts_captured_at",
        "incoming_inspection_booked": "incoming_inspection_booked_at",
        "deposit_banked_trust": "deposit_banked_trust_at",
    }

    def update(self, instance: TenantOnboarding, validated_data: dict) -> TenantOnboarding:
        now = timezone.now()
        for flag, ts_field in self._TIMESTAMP_MAP.items():
            if flag in validated_data:
                new_val = validated_data[flag]
                # Only stamp timestamp when transitioning False → True
                if new_val and not getattr(instance, flag):
                    validated_data[ts_field] = now

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Auto-complete when all v1 items are ticked
        if instance.is_complete and instance.completed_at is None:
            instance.completed_at = now

        instance.save()
        return instance


class TenantOnboardingCreateSerializer(serializers.Serializer):
    """Input serializer for creating an onboarding record for a lease."""

    lease_id = serializers.PrimaryKeyRelatedField(queryset=Lease.objects.all(), source="lease")

    def validate(self, data):
        lease = data["lease"]
        if TenantOnboarding.objects.filter(lease=lease).exists():
            raise serializers.ValidationError(
                {"lease_id": "An onboarding record already exists for this lease."}
            )
        return data

    def create(self, validated_data):
        return TenantOnboarding.objects.create(lease=validated_data["lease"])


class AssignUnitSerializer(serializers.Serializer):
    """Input serializer for the assign-unit action."""

    tenant_id = serializers.PrimaryKeyRelatedField(queryset=Tenant.objects.all())
    unit_id = serializers.PrimaryKeyRelatedField(queryset=Unit.objects.all())
    start_date = serializers.DateField()
    end_date = serializers.DateField(required=False, allow_null=True, default=None)
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, data):
        if data["end_date"] and data["end_date"] < data["start_date"]:
            raise serializers.ValidationError(
                {"end_date": "End date must be on or after start date."}
            )
        return data
