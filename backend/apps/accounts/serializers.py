import uuid

from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, Person, Agency, PersonDocument


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    account_type = serializers.ChoiceField(
        choices=Agency.AccountType.choices,
        default=Agency.AccountType.INDIVIDUAL,
        write_only=True,
    )
    agency_name = serializers.CharField(required=False, allow_blank=True, write_only=True, default="")

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "phone", "password", "account_type", "agency_name"]

    def validate_email(self, value):
        email = value.strip().lower()
        # Only reject if an ACTIVE user already owns this email.
        # Soft-deleted (inactive) users are allowed to re-register — the old record
        # will have its email rewritten in create() to free the unique constraint.
        if User.objects.filter(email=email, is_active=True).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email

    def validate_password(self, value):
        from django.contrib.auth.password_validation import validate_password
        validate_password(value)
        return value

    def validate(self, data):
        if data.get("account_type") == Agency.AccountType.AGENCY and not data.get("agency_name", "").strip():
            raise serializers.ValidationError({"agency_name": "Agency name is required for estate agency accounts."})
        return data

    def create(self, validated_data):
        account_type = validated_data.pop("account_type", Agency.AccountType.INDIVIDUAL)
        agency_name = validated_data.pop("agency_name", "")

        # Free the unique-email constraint on any soft-deleted user so the new
        # registration can claim the address. Audit-log rows, leases, and other
        # historical records remain attached to the original row.
        email = validated_data["email"]
        User.objects.filter(email=email, is_active=False).update(
            email=f"deleted_{uuid.uuid4().hex[:8]}_{email}"
        )

        # Assign role based on account type
        role = User.Role.AGENCY_ADMIN if account_type == Agency.AccountType.AGENCY else User.Role.OWNER

        user = User.objects.create_user(**validated_data, role=role)

        # Create an Agency and link it to the user
        if account_type == Agency.AccountType.AGENCY:
            name = agency_name.strip()
        else:
            name = f"{validated_data.get('first_name', '')} {validated_data.get('last_name', '')}".strip() or user.email
        agency = Agency.objects.create(account_type=account_type, name=name)
        user.agency = agency
        user.save(update_fields=["agency"])

        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(email=data["email"], password=data["password"])
        if not user:
            raise serializers.ValidationError("Invalid credentials.")
        if not user.is_active:
            raise serializers.ValidationError("Account is disabled.")
        refresh = RefreshToken.for_user(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        }


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "full_name", "phone", "role", "date_joined"]
        read_only_fields = ["id", "email", "role", "date_joined"]


class PersonDocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = PersonDocument
        fields = ['id', 'document_type', 'file', 'file_url', 'description', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']

    def get_file_url(self, obj):
        request = self.context.get('request')
        return request.build_absolute_uri(obj.file.url) if obj.file and request else None


class PersonSerializer(serializers.ModelSerializer):
    documents = PersonDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Person
        fields = [
            "id", "person_type", "full_name", "id_number", "phone", "email",
            "address", "employer", "occupation", "monthly_income", "date_of_birth",
            "emergency_contact_name", "emergency_contact_phone",
            "company_reg", "vat_number", "linked_user", "created_at",
            "documents",
        ]
        read_only_fields = ["id", "created_at"]


class TenantListSerializer(serializers.ModelSerializer):
    """
    Lighter projection for /auth/tenants/. Reports `is_active` based on
    whether the Person is attached to any lease with status='active'
    (as primary tenant OR co-tenant). Relies on annotations provided by
    TenantsListView.get_queryset().
    """
    is_active = serializers.SerializerMethodField()
    date_joined = serializers.SerializerMethodField()

    class Meta:
        model = Person
        fields = ["id", "email", "full_name", "phone", "id_number", "date_joined", "is_active"]

    def get_is_active(self, obj) -> bool:
        primary = getattr(obj, "active_primary_lease_count", 0) or 0
        cotenant = getattr(obj, "active_cotenant_lease_count", 0) or 0
        return (primary + cotenant) > 0

    def get_date_joined(self, obj):
        user = obj.linked_user
        if user and user.date_joined:
            return user.date_joined.isoformat()
        return obj.created_at.isoformat() if obj.created_at else None


class AdminUserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    agency_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name", "full_name",
            "phone", "role", "is_active", "date_joined", "last_login",
            "agency", "agency_name", "module_access", "ffc_number", "ffc_category",
        ]
        read_only_fields = ["id", "email", "date_joined", "last_login"]

    def get_agency_name(self, obj):
        return obj.agency.name if obj.agency else None


class AdminUserUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=User.Role.choices, required=False)
    is_active = serializers.BooleanField(required=False)
    agency = serializers.PrimaryKeyRelatedField(
        queryset=Agency.objects.all(), required=False, allow_null=True,
    )
    module_access = serializers.ListField(
        child=serializers.CharField(), required=False, default=list,
    )
    ffc_number = serializers.CharField(required=False, allow_blank=True)
    ffc_category = serializers.ChoiceField(
        choices=User.FFCCategory.choices, required=False, allow_blank=True,
    )


class InviteUserSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=User.Role.choices)
    first_name = serializers.CharField(required=False, allow_blank=True, default="")
    agency_id = serializers.IntegerField(required=False, allow_null=True)


class AgencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Agency
        fields = [
            "id", "account_type",
            # Identity
            "name", "trading_name", "registration_number", "vat_number", "eaab_ffc_number",
            # Contact
            "contact_number", "email", "physical_address", "postal_address", "website",
            # Trust account
            "trust_account_number", "trust_bank_name", "trust_branch_code",
            # Compliance
            "principal_name", "principal_ppra_number",
            "auditor_name", "auditor_irba_number",
            "bee_level", "fica_registered",
            # Financial cycle
            "statement_date", "disbursement_date", "information_officer_email",
            # Branding
            "logo",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]


class OTPSendSerializer(serializers.Serializer):
    phone = serializers.CharField()


class OTPVerifySerializer(serializers.Serializer):
    phone = serializers.CharField()
    code = serializers.CharField(max_length=6)
