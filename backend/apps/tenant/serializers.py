from rest_framework import serializers

from apps.accounts.models import Person
from apps.leases.models import Lease
from apps.properties.models import Unit

from .models import Tenant, TenantUnitAssignment


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
