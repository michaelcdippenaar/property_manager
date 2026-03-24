import random
from django.utils import timezone
from datetime import timedelta
from rest_framework import status, generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView

from .models import User, OTPCode, Person, PushToken
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer, OTPSendSerializer, OTPVerifySerializer, PersonSerializer


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
        from core.notifications import send_sms_otp
        send_sms_otp(phone, code)

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


class PushTokenView(APIView):
    """Register or refresh an FCM/APNs push token for the authenticated user."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get("token", "").strip()
        platform = request.data.get("platform", "").strip().lower()
        if not token:
            return Response({"detail": "token is required."}, status=status.HTTP_400_BAD_REQUEST)
        if platform not in ("ios", "android"):
            return Response({"detail": "platform must be 'ios' or 'android'."}, status=status.HTTP_400_BAD_REQUEST)

        PushToken.objects.update_or_create(
            user=request.user,
            token=token,
            defaults={"platform": platform},
        )
        return Response({"detail": "Token registered."})

    def delete(self, request):
        token = request.data.get("token", "").strip()
        if token:
            PushToken.objects.filter(user=request.user, token=token).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TenantsListView(generics.ListAPIView):
    """
    Returns all Person records who appear on at least one lease
    (as primary tenant or co-tenant).
    """
    serializer_class = PersonSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from django.db.models import Q, Count
        qs = Person.objects.filter(
            Q(leases_as_primary__isnull=False) | Q(co_tenancies__isnull=False)
        ).distinct().annotate(
            active_lease_count=Count(
                'leases_as_primary',
                filter=Q(leases_as_primary__status='active')
            )
        ).order_by('full_name')
        return qs


class PersonViewSet(generics.ListCreateAPIView):
    serializer_class = PersonSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Person.objects.all()
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(full_name__icontains=q)
        return qs


class PersonDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = PersonSerializer
    permission_classes = [IsAuthenticated]
    queryset = Person.objects.all()
