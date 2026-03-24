from rest_framework import serializers
from apps.accounts.models import Person
from .models import Lease, LeaseTenant, LeaseOccupant, LeaseGuarantor, LeaseDocument


class PersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Person
        fields = ["id", "person_type", "full_name", "id_number", "phone", "email", "company_reg", "vat_number"]


class LeaseTenantSerializer(serializers.ModelSerializer):
    person = PersonSerializer(read_only=True)
    person_id = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.all(), source="person", write_only=True
    )

    class Meta:
        model = LeaseTenant
        fields = ["id", "person", "person_id"]


class LeaseOccupantSerializer(serializers.ModelSerializer):
    person = PersonSerializer(read_only=True)
    person_id = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.all(), source="person", write_only=True
    )

    class Meta:
        model = LeaseOccupant
        fields = ["id", "person", "person_id", "relationship_to_tenant"]


class LeaseGuarantorSerializer(serializers.ModelSerializer):
    person = PersonSerializer(read_only=True)
    person_id = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.all(), source="person", write_only=True
    )
    covers_tenant = PersonSerializer(read_only=True)
    covers_tenant_id = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.all(), source="covers_tenant", write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = LeaseGuarantor
        fields = ["id", "person", "person_id", "covers_tenant", "covers_tenant_id"]


class LeaseDocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = LeaseDocument
        fields = ["id", "document_type", "file", "file_url", "description", "uploaded_by", "uploaded_at"]
        read_only_fields = ["uploaded_by", "uploaded_at"]

    def get_file_url(self, obj):
        request = self.context.get("request")
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


class LeaseSerializer(serializers.ModelSerializer):
    documents = LeaseDocumentSerializer(many=True, read_only=True)
    co_tenants = LeaseTenantSerializer(many=True, read_only=True)
    occupants = LeaseOccupantSerializer(many=True, read_only=True)
    guarantors = LeaseGuarantorSerializer(many=True, read_only=True)
    primary_tenant_detail = PersonSerializer(source="primary_tenant", read_only=True)
    tenant_name = serializers.CharField(source="primary_tenant.full_name", read_only=True, default="")
    unit_label = serializers.SerializerMethodField()

    class Meta:
        model = Lease
        fields = "__all__"
        read_only_fields = ["created_at"]

    def get_unit_label(self, obj):
        return f"{obj.unit.property.name} — Unit {obj.unit.unit_number}"
