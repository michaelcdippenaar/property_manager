import random
from django.utils import timezone
from datetime import timedelta
from rest_framework import status, generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView

from .models import User, OTPCode
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer, OTPSendSerializer, OTPVerifySerializer


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class OTPSendView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone"]

        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            # Don't reveal whether phone exists
            return Response({"detail": "OTP sent if phone is registered."})

        code = f"{random.randint(100000, 999999)}"
        OTPCode.objects.create(user=user, code=code)
        # TODO: integrate SMS provider (e.g. Twilio, Africa's Talking)
        print(f"[DEV] OTP for {phone}: {code}")

        return Response({"detail": "OTP sent if phone is registered."})


class OTPVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone"]
        code = serializer.validated_data["code"]
        expiry = timezone.now() - timedelta(minutes=10)

        try:
            user = User.objects.get(phone=phone)
            otp = OTPCode.objects.filter(
                user=user, code=code, is_used=False, created_at__gte=expiry
            ).latest("created_at")
        except (User.DoesNotExist, OTPCode.DoesNotExist):
            return Response({"detail": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)

        otp.is_used = True
        otp.save()

        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        })


class TenantsListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return User.objects.filter(role=User.Role.TENANT)
