import logging
import uuid

from django.contrib.auth import authenticate
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from utils.http import get_client_ip
from .models import User, Person, Agency, PersonDocument

logger = logging.getLogger(__name__)


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    account_type = serializers.ChoiceField(
        choices=Agency.AccountType.choices,
        default=Agency.AccountType.INDIVIDUAL,
        write_only=True,
    )
    agency_name = serializers.CharField(required=False, allow_blank=True, write_only=True, default="")
    # POPIA s11 — IDs of the current ToS and Privacy Policy documents that the
    # user explicitly accepted during registration. Both are optional so that
    # programmatic / test registrations are not hard-blocked, but the consent
    # rows are created server-side when the IDs are supplied so the audit trail
    # carries the correct IP + user-agent at the moment of registration.
    tos_document_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    privacy_document_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = User
        fields = [
            "email", "first_name", "last_name", "phone", "password",
            "account_type", "agency_name",
            "tos_document_id", "privacy_document_id",
        ]

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
        # Pop consent IDs — not model fields; handled separately below.
        tos_document_id = validated_data.pop("tos_document_id", None)
        privacy_document_id = validated_data.pop("privacy_document_id", None)

        # Phase 3.1 — Agency MUST be created before the User so the user is
        # never persisted without an agency_id (Tanja-bug class). The whole
        # block runs in a single atomic transaction.
        email = validated_data["email"]

        if account_type == Agency.AccountType.AGENCY:
            agency_display_name = agency_name.strip()
        else:
            # Individual landlord — auto-create a personal "<First Last>'s Properties"
            # agency so they too own a tenant namespace from day 1. They can rename it.
            first = (validated_data.get("first_name") or "").strip()
            last = (validated_data.get("last_name") or "").strip()
            full = f"{first} {last}".strip()
            if full:
                agency_display_name = f"{full}'s Properties"
            else:
                agency_display_name = f"{email}'s Properties"

        # Both account types create an Agency + AGENCY_ADMIN-or-OWNER user atomically.
        # AGENCY → AGENCY_ADMIN; INDIVIDUAL landlord → AGENCY_ADMIN of their personal
        # workspace (they ARE the agency for their own properties; OWNER role was the
        # legacy semantics that produced orphans).
        role = User.Role.AGENCY_ADMIN

        with transaction.atomic():
            # Free the unique-email constraint on any soft-deleted user so the new
            # registration can claim the address. Audit-log rows, leases, and other
            # historical records remain attached to the original row.
            User.objects.filter(email=email, is_active=False).update(
                email=f"deleted_{uuid.uuid4().hex[:8]}_{email}"
            )

            agency = Agency.objects.create(
                account_type=account_type,
                name=agency_display_name,
            )
            user = User.objects.create_user(
                **validated_data,
                role=role,
                agency=agency,
            )

        # Seed starter content OUTSIDE the registration transaction — failure
        # to seed is logged but must NOT roll back account creation.
        try:
            from .starter_content import seed_starter_content
            seed_starter_content(agency)
        except Exception:  # pragma: no cover — defensive; seed_starter_content already swallows
            logger.exception(
                "starter_content seeding failed for agency %s; account creation kept", agency.pk
            )

        # POPIA s11 — persist UserConsent rows for any document IDs supplied.
        request = self.context.get("request")
        self._record_consent(user, tos_document_id, request)
        self._record_consent(user, privacy_document_id, request)

        return user

    @staticmethod
    def _record_consent(user, document_id, request):
        """Create a UserConsent row for the given document ID, if supplied and valid."""
        if not document_id:
            return
        from apps.legal.models import LegalDocument, UserConsent
        try:
            doc = LegalDocument.objects.get(pk=document_id, is_current=True)
        except LegalDocument.DoesNotExist:
            # Stale or invalid ID — skip silently; registration still succeeds.
            return
        ip = None
        ua = ""
        if request:
            ip = get_client_ip(request)
            ua = request.META.get("HTTP_USER_AGENT", "")[:500]
        UserConsent.objects.get_or_create(
            user=user,
            document=doc,
            defaults={"ip_address": ip, "user_agent": ua},
        )


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(email=data["email"], password=data["password"])
        if not user:
            raise serializers.ValidationError("Invalid credentials.")
        if not user.is_active:
            raise serializers.ValidationError("Account is disabled.")
        # Return the user object; the view decides whether to issue full tokens
        # or a partial two_fa_token depending on 2FA state.
        return {"user": user}


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    twofa_enrolled = serializers.SerializerMethodField()
    twofa_required = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "full_name", "phone", "role", "date_joined",
                  "twofa_enrolled", "twofa_required", "seen_welcome_at", "two_fa_method"]
        read_only_fields = ["id", "email", "role", "date_joined", "twofa_enrolled", "twofa_required"]

    def get_twofa_enrolled(self, obj) -> bool:
        from .models import UserTOTP
        try:
            return obj.totp.is_active
        except UserTOTP.DoesNotExist:
            return False

    def get_twofa_required(self, obj) -> bool:
        from .models import TOTP_REQUIRED_ROLES
        return obj.role in TOTP_REQUIRED_ROLES


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
