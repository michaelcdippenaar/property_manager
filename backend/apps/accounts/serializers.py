from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, Person, Agency


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "phone", "password"]

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email

    def validate_password(self, value):
        from django.contrib.auth.password_validation import validate_password
        validate_password(value)
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


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


class PersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Person
        fields = [
            "id", "person_type", "full_name", "id_number", "phone", "email",
            "address", "employer", "occupation", "date_of_birth",
            "emergency_contact_name", "emergency_contact_phone",
            "company_reg", "vat_number", "linked_user", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class AdminUserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name", "full_name",
            "phone", "role", "is_active", "date_joined", "last_login",
        ]
        read_only_fields = ["id", "email", "date_joined", "last_login"]


class AdminUserUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=User.Role.choices, required=False)
    is_active = serializers.BooleanField(required=False)


class InviteUserSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=User.Role.choices)
    first_name = serializers.CharField(required=False, allow_blank=True, default="")


class AgencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Agency
        fields = [
            "id", "name", "registration_number", "eaab_ffc_number",
            "contact_number", "email", "physical_address",
            "trust_account_number", "trust_bank_name",
            "statement_date", "disbursement_date", "information_officer_email",
            "logo", "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]


class OTPSendSerializer(serializers.Serializer):
    phone = serializers.CharField()


class OTPVerifySerializer(serializers.Serializer):
    phone = serializers.CharField()
    code = serializers.CharField(max_length=6)
