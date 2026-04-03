import re
from rest_framework import serializers
from apps.accounts.models import Person
from .models import Lease, LeaseEvent, LeaseTenant, LeaseOccupant, LeaseGuarantor, LeaseDocument, LeaseTemplate, LeaseBuilderSession, OnboardingStep, ReusableClause


def _detect_and_group(content_html):
    if not content_html:
        return {}
    names = list(dict.fromkeys(re.findall(r'data-merge-field="([^"]+)"', content_html)))
    groups = {'landlord': [], 'property': [], 'tenant_1': [], 'tenant_2': [], 'tenant_3': [], 'lease_terms': [], 'other': []}
    for f in names:
        fl = f.lower()
        if fl.startswith('landlord_'):
            groups['landlord'].append(f)
        elif fl.startswith('tenant_2') or fl.startswith('co_tenant'):
            groups['tenant_2'].append(f)
        elif fl.startswith('tenant_3'):
            groups['tenant_3'].append(f)
        elif fl.startswith('tenant_') or f in ('tenant_name', 'tenant_id', 'tenant_phone', 'tenant_email', 'tenant_full_name'):
            groups['tenant_1'].append(f)
        elif any(fl.startswith(p) for p in ('property_', 'unit_', 'city', 'province', 'address')):
            groups['property'].append(f)
        elif any(fl.startswith(p) or f == p for p in ('lease_', 'monthly_rent', 'deposit', 'escalation', 'notice', 'water_', 'electricity', 'pets', 'max_occupants', 'payment')):
            groups['lease_terms'].append(f)
        else:
            groups['other'].append(f)
    return {k: v for k, v in groups.items() if v}


class PersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Person
        fields = [
            "id", "person_type", "full_name", "id_number", "phone", "email",
            "address", "employer", "occupation", "date_of_birth",
            "emergency_contact_name", "emergency_contact_phone",
            "company_reg", "vat_number",
        ]


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
    # Kept for backwards compat — first signatory name only
    tenant_name = serializers.CharField(source="primary_tenant.full_name", read_only=True, default="")
    # All signatories (primary + co-tenants) — equally important
    all_tenant_names = serializers.SerializerMethodField()
    document_count = serializers.SerializerMethodField()
    unit_label = serializers.SerializerMethodField()
    landlord_info = serializers.SerializerMethodField()
    property_id = serializers.IntegerField(source='unit.property_id', read_only=True)

    class Meta:
        model = Lease
        fields = "__all__"
        read_only_fields = ["created_at"]

    def get_unit_label(self, obj):
        return f"{obj.unit.property.name} — Unit {obj.unit.unit_number}"

    def get_all_tenant_names(self, obj):
        names = []
        if obj.primary_tenant:
            names.append(obj.primary_tenant.full_name)
        for ct in obj.co_tenants.all():
            if ct.person.full_name:
                names.append(ct.person.full_name)
        return names

    def get_document_count(self, obj):
        return obj.documents.count()

    def get_landlord_info(self, obj):
        from apps.esigning.services import _get_landlord_info
        return _get_landlord_info(obj)


class LeaseTemplateSerializer(serializers.ModelSerializer):
    detected_variables = serializers.SerializerMethodField()

    class Meta:
        model = LeaseTemplate
        fields = ["id", "name", "version", "province", "fields_schema", "is_active", "created_at", "updated_at", "content_html", "header_html", "footer_html", "detected_variables", "docx_file"]
        read_only_fields = ["created_at", "updated_at"]

    def get_detected_variables(self, obj):
        return _detect_and_group(obj.content_html or "")


class ReusableClauseSerializer(serializers.ModelSerializer):
    source_template_names = serializers.SerializerMethodField()

    class Meta:
        model = ReusableClause
        fields = [
            "id", "title", "category", "html", "tags",
            "use_count", "source_template_names", "created_at",
        ]
        read_only_fields = ["created_at", "use_count", "source_template_names"]

    def get_source_template_names(self, obj):
        return list(obj.source_templates.values_list("name", flat=True))


class LeaseBuilderSessionSerializer(serializers.ModelSerializer):
    missing_fields = serializers.SerializerMethodField()

    class Meta:
        model = LeaseBuilderSession
        fields = [
            "id", "status", "current_state", "rha_flags", "messages",
            "missing_fields", "created_at", "updated_at",
            "lease",
        ]
        read_only_fields = ["created_at", "updated_at", "lease"]

    def get_missing_fields(self, obj):
        required = [
            "landlord_name", "property_address", "unit_number", "tenant_name",
            "lease_start", "lease_end", "monthly_rent", "deposit", "notice_period_days",
        ]
        return [f for f in required if not obj.current_state.get(f)]


class LeaseEventSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source="get_event_type_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    lease_label = serializers.SerializerMethodField()
    property_name = serializers.SerializerMethodField()

    class Meta:
        model = LeaseEvent
        fields = [
            "id", "lease", "event_type", "type_label", "title", "description",
            "date", "status", "status_label", "is_recurring", "recurrence_day",
            "completed_at", "completed_by", "lease_label", "property_name", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_lease_label(self, obj):
        tenant = obj.lease.primary_tenant
        return tenant.full_name if tenant else f"Lease #{obj.lease.id}"

    def get_property_name(self, obj):
        try:
            return obj.lease.unit.property.name
        except AttributeError:
            return ""


class OnboardingStepSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source="get_step_type_display", read_only=True)

    class Meta:
        model = OnboardingStep
        fields = [
            "id", "lease", "step_type", "type_label", "title",
            "is_completed", "completed_at", "completed_by", "notes", "order", "created_at",
        ]
        read_only_fields = ["id", "created_at"]
