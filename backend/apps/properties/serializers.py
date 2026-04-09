from rest_framework import serializers
from .models import (
    BankAccount, ComplianceCertificate, InsurancePolicy, Landlord, LandlordDocument,
    Property, PropertyAgentConfig, PropertyDocument, PropertyGroup, PropertyOwnership,
    PropertyPhoto, PropertyValuation, PropertyViewing, Unit, UnitInfo,
)


class UnitSerializer(serializers.ModelSerializer):
    active_lease_info = serializers.SerializerMethodField()
    open_maintenance_count = serializers.SerializerMethodField()

    class Meta:
        model = Unit
        fields = "__all__"

    def get_open_maintenance_count(self, obj):
        from apps.maintenance.models import MaintenanceRequest
        return MaintenanceRequest.objects.filter(
            unit=obj, status__in=["open", "in_progress"]
        ).count()

    def get_active_lease_info(self, obj):
        from apps.leases.models import Lease
        lease = (
            Lease.objects.filter(unit=obj, status="active")
            .select_related("primary_tenant")
            .order_by("-start_date")
            .first()
        )
        if not lease:
            return None
        return {
            "start_date": lease.start_date.isoformat(),
            "end_date": lease.end_date.isoformat(),
            "tenant_name": lease.primary_tenant.full_name if lease.primary_tenant else None,
            "monthly_rent": str(lease.monthly_rent),
            "status": lease.status,
        }


class PropertySerializer(serializers.ModelSerializer):
    units = UnitSerializer(many=True, read_only=True)
    unit_count = serializers.IntegerField(source="units.count", read_only=True)
    nearest_lease_expiry = serializers.SerializerMethodField()
    cover_photo = serializers.SerializerMethodField()
    property_active_lease_info = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = "__all__"

    def create(self, validated_data):
        if "agent" not in validated_data:
            validated_data["agent"] = self.context["request"].user
        return super().create(validated_data)

    def get_nearest_lease_expiry(self, obj):
        from apps.leases.models import Lease
        lease = (
            Lease.objects.filter(unit__property=obj, status="active")
            .order_by("end_date")
            .values("start_date", "end_date")
            .first()
        )
        if not lease:
            return None
        return {
            "start_date": lease["start_date"].isoformat(),
            "end_date": lease["end_date"].isoformat(),
        }

    def get_property_active_lease_info(self, obj):
        """Active lease at the property level (used when the property has no units)."""
        if obj.units.exists():
            return None
        from apps.leases.models import Lease
        lease = (
            Lease.objects.filter(unit__property=obj, status="active")
            .select_related("primary_tenant")
            .order_by("-start_date")
            .first()
        )
        if not lease:
            return None
        return {
            "start_date": lease.start_date.isoformat(),
            "end_date": lease.end_date.isoformat(),
            "tenant_name": lease.primary_tenant.full_name if lease.primary_tenant else None,
            "monthly_rent": str(lease.monthly_rent),
            "status": lease.status,
        }

    def get_cover_photo(self, obj):
        photo = obj.photos.first()
        if photo and photo.photo:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(photo.photo.url)
            return photo.photo.url
        return None


class UnitInfoSerializer(serializers.ModelSerializer):
    unit_number = serializers.CharField(source="unit.unit_number", read_only=True, default=None)
    property_name = serializers.CharField(source="property.name", read_only=True)

    class Meta:
        model = UnitInfo
        fields = ["id", "property", "property_name", "unit", "unit_number", "icon_type", "label", "value", "sort_order", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class PropertyAgentConfigSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)

    class Meta:
        model = PropertyAgentConfig
        fields = ["id", "property", "property_name", "maintenance_playbook", "ai_notes", "is_active", "updated_at"]
        read_only_fields = ["id", "updated_at"]


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class LandlordDocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = LandlordDocument
        fields = ['id', 'landlord', 'filename', 'file_url', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at', 'file_url']

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


class LandlordSerializer(serializers.ModelSerializer):
    bank_accounts = BankAccountSerializer(many=True, read_only=True)
    property_count = serializers.SerializerMethodField()
    properties = serializers.SerializerMethodField()

    class Meta:
        model = Landlord
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_property_count(self, obj):
        return obj.ownerships.filter(is_current=True).count()

    def get_properties(self, obj):
        return [
            {'id': o.property_id, 'name': o.property.name, 'ownership_id': o.id}
            for o in obj.ownerships.filter(is_current=True).select_related('property')
        ]


class PropertyOwnershipSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)
    landlord_name = serializers.CharField(source="landlord.name", read_only=True, default=None)

    class Meta:
        model = PropertyOwnership
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]

    def to_representation(self, instance):
        """Fall back to linked Landlord fields when denormalized ownership fields are empty.

        Ownership records are sometimes created with only `landlord` FK set, leaving the
        denormalized owner_*/representative_*/bank_details fields blank. For display,
        resolve them from the linked Landlord so the UI shows the correct owner info.
        """
        data = super().to_representation(instance)
        ll = instance.landlord
        if not ll:
            return data

        def _fallback(field, value):
            if not data.get(field):
                data[field] = value

        _fallback("owner_name", ll.name)
        _fallback("owner_type", ll.landlord_type)
        _fallback("registration_number", ll.registration_number)
        _fallback("vat_number", ll.vat_number)
        _fallback("owner_email", ll.email)
        _fallback("owner_phone", ll.phone)
        if not data.get("owner_address"):
            data["owner_address"] = ll.address or {}

        _fallback("representative_name", ll.representative_name)
        _fallback("representative_id_number", ll.representative_id_number)
        _fallback("representative_email", ll.representative_email)
        _fallback("representative_phone", ll.representative_phone)

        if not data.get("bank_details"):
            default_ba = (
                ll.bank_accounts.filter(is_default=True).first()
                or ll.bank_accounts.first()
            )
            if default_ba:
                data["bank_details"] = {
                    "bank_name": default_ba.bank_name,
                    "branch_code": default_ba.branch_code,
                    "account_number": default_ba.account_number,
                    "account_type": default_ba.account_type,
                    "account_holder": default_ba.account_holder,
                }

        return data


class PropertyPhotoSerializer(serializers.ModelSerializer):
    photo_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = PropertyPhoto
        fields = ["id", "property", "unit", "photo", "photo_url", "thumbnail_url", "caption", "category", "position", "is_cover", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]

    def get_photo_url(self, obj):
        request = self.context.get("request")
        if obj.photo and request:
            return request.build_absolute_uri(obj.photo.url)
        return None

    def get_thumbnail_url(self, obj):
        request = self.context.get("request")
        if obj.thumbnail and request:
            return request.build_absolute_uri(obj.thumbnail.url)
        # Fall back to full photo if no thumbnail yet
        if obj.photo and request:
            return request.build_absolute_uri(obj.photo.url)
        return None


class PropertyDocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = PropertyDocument
        fields = ["id", "property", "unit", "document", "file_url", "doc_type", "name", "notes", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]

    def get_file_url(self, obj):
        request = self.context.get("request")
        if obj.document and request:
            return request.build_absolute_uri(obj.document.url)
        return None


class ComplianceCertificateSerializer(serializers.ModelSerializer):
    cert_type_display = serializers.CharField(source="get_cert_type_display", read_only=True)
    status = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ComplianceCertificate
        fields = [
            "id", "property", "cert_type", "cert_type_display", "certificate_number",
            "issued_date", "expiry_date", "contractor_name", "contractor_phone",
            "contractor_email", "registration_number", "document", "file_url",
            "notes", "created_at", "status",
        ]
        read_only_fields = ["id", "created_at"]

    def get_status(self, obj):
        return obj.get_status()

    def get_file_url(self, obj):
        request = self.context.get("request")
        if obj.document and request:
            return request.build_absolute_uri(obj.document.url)
        return None


class InsurancePolicySerializer(serializers.ModelSerializer):
    policy_type_display = serializers.CharField(source="get_policy_type_display", read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = InsurancePolicy
        fields = [
            "id", "property", "policy_type", "policy_type_display", "insurer",
            "policy_number", "broker", "broker_email", "broker_phone",
            "sum_insured", "monthly_premium", "excess", "start_date", "end_date",
            "is_active", "document", "file_url", "notes", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_file_url(self, obj):
        request = self.context.get("request")
        if obj.document and request:
            return request.build_absolute_uri(obj.document.url)
        return None


class PropertyValuationSerializer(serializers.ModelSerializer):
    valuation_type_display = serializers.CharField(source="get_valuation_type_display", read_only=True)

    class Meta:
        model = PropertyValuation
        fields = [
            "id", "property", "valuation_type", "valuation_type_display",
            "amount", "valuation_date", "valuator", "notes", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class PropertyGroupSerializer(serializers.ModelSerializer):
    property_count = serializers.IntegerField(source="properties.count", read_only=True)
    property_ids = serializers.PrimaryKeyRelatedField(
        source="properties", queryset=Property.objects.all(),
        many=True, required=False,
    )

    class Meta:
        model = PropertyGroup
        fields = ["id", "name", "description", "property_ids", "property_count", "created_at"]
        read_only_fields = ["created_at"]

    def create(self, validated_data):
        props = validated_data.pop("properties", [])
        group = PropertyGroup.objects.create(**validated_data)
        if props:
            group.properties.set(props)
        return group

    def update(self, instance, validated_data):
        props = validated_data.pop("properties", None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if props is not None:
            instance.properties.set(props)
        return instance


class PropertyViewingSerializer(serializers.ModelSerializer):
    prospect_name = serializers.CharField(source="prospect.full_name", read_only=True)
    property_name = serializers.CharField(source="property.name", read_only=True)
    unit_number   = serializers.SerializerMethodField()
    agent_name    = serializers.SerializerMethodField()
    prospect_detail = serializers.SerializerMethodField()

    class Meta:
        model  = PropertyViewing
        fields = [
            "id", "property", "property_name",
            "unit", "unit_number",
            "prospect", "prospect_name", "prospect_detail",
            "agent", "agent_name",
            "scheduled_at", "duration_minutes", "status",
            "notes", "converted_to_lease",
            "created_at", "updated_at",
        ]
        read_only_fields = ["converted_to_lease", "created_at", "updated_at"]

    def get_unit_number(self, obj):
        return obj.unit.unit_number if obj.unit else None

    def get_agent_name(self, obj):
        return obj.agent.get_full_name() if obj.agent else None

    def get_prospect_detail(self, obj):
        from apps.accounts.serializers import PersonSerializer
        return PersonSerializer(obj.prospect, context=self.context).data
