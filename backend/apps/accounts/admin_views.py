from django.db.models import Q
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import User, UserInvite, Agency
from .permissions import IsAdmin
from .serializers import AdminUserSerializer, AdminUserUpdateSerializer, InviteUserSerializer, AgencySerializer


class UserListView(generics.ListAPIView):
    """List all users. Filterable by role and searchable by email/name."""
    permission_classes = [IsAdmin]
    serializer_class = AdminUserSerializer

    def get_queryset(self):
        qs = User.objects.all()
        # Hide inactive (deleted) users unless explicitly requested
        if self.request.query_params.get("include_inactive") != "true":
            qs = qs.filter(is_active=True)
        role = self.request.query_params.get("role")
        if role:
            qs = qs.filter(role=role)
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )
        return qs


class UserDetailView(APIView):
    """Retrieve, update, or soft-delete a user (admin only)."""
    permission_classes = [IsAdmin]

    def get(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(AdminUserSerializer(user).data)

    def patch(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = AdminUserUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if "role" in serializer.validated_data and user.pk == request.user.pk:
            return Response(
                {"detail": "You cannot change your own role."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for field, value in serializer.validated_data.items():
            setattr(user, field, value)
        user.save()
        return Response(AdminUserSerializer(user).data)

    def delete(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        user.is_active = False
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PendingInvitesView(generics.ListAPIView):
    """List pending (unaccepted) invites."""
    permission_classes = [IsAdmin]

    def get(self, request, *args, **kwargs):
        invites = UserInvite.objects.filter(accepted_at__isnull=True).order_by("-created_at")
        data = [
            {
                "id": inv.id,
                "email": inv.email,
                "role": inv.role,
                "token": str(inv.token),
                "invited_by": inv.invited_by.full_name if inv.invited_by else None,
                "created_at": inv.created_at.isoformat(),
            }
            for inv in invites
        ]
        return Response(data)


class InviteUserView(APIView):
    """Send an invite to a new user (admin only)."""
    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = InviteUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].strip().lower()
        role = serializer.validated_data["role"]
        first_name = serializer.validated_data.get("first_name", "")

        if User.objects.filter(email=email).exists():
            return Response(
                {"detail": "A user with this email already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invite = UserInvite.objects.create(
            email=email,
            role=role,
            invited_by=request.user,
        )

        # Send invite email (best-effort)
        try:
            from apps.notifications.services import send_email

            from django.conf import settings
            base_url = getattr(settings, "SIGNING_PUBLIC_APP_BASE_URL", "") or "http://localhost:5173"
            invite_url = f"{base_url}/accept-invite?token={invite.token}"

            greeting = f"Hi {first_name},\n\n" if first_name else "Hi,\n\n"
            body = (
                f"{greeting}"
                f"You've been invited to join Klikk as a {role}.\n"
                f"Click the link below to accept your invitation:\n"
                f"{invite_url}\n\n"
                f"This invitation was sent by {request.user.full_name}."
            )
            html_body = (
                f"<p>{greeting.strip()}</p>"
                f"<p>You've been invited to join Klikk as a <strong>{role}</strong>.</p>"
                f'<p><a href="{invite_url}">Accept Invitation</a></p>'
                f"<p>This invitation was sent by {request.user.full_name}.</p>"
            )
            send_email(
                subject="You've been invited to Klikk",
                body=body,
                to_emails=email,
                html_body=html_body,
            )
        except Exception:
            pass

        return Response(
            {"detail": "Invitation sent.", "token": str(invite.token)},
            status=status.HTTP_201_CREATED,
        )


class AgencySettingsView(APIView):
    """
    GET  → retrieve the singleton Agency record (or empty {}).
    PUT  → create-or-update (upsert) the Agency record.
    Supports multipart/form-data for logo uploads.
    """
    permission_classes = [IsAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        agency = Agency.get_solo()
        if not agency:
            return Response({}, status=status.HTTP_200_OK)
        return Response(AgencySerializer(agency).data)

    def put(self, request):
        agency = Agency.get_solo()
        if agency:
            serializer = AgencySerializer(agency, data=request.data, partial=True)
        else:
            serializer = AgencySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
