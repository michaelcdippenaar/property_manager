from django.db.models import Q
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import User, UserInvite, Agency
from .permissions import IsAdmin, IsAgentOrAdmin
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
    """List pending (unaccepted, uncancelled) invites."""
    permission_classes = [IsAdmin]

    def get(self, request, *args, **kwargs):
        invites = (
            UserInvite.objects
            .filter(accepted_at__isnull=True, cancelled_at__isnull=True)
            .select_related("invited_by")
            .order_by("-created_at")
        )
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


class CancelInviteView(APIView):
    """Cancel (revoke) a pending invite. The token becomes unusable and the
    recipient will see an 'Invitation Expired' page if they click the link."""
    permission_classes = [IsAdmin]

    def delete(self, request, pk):
        from django.utils import timezone
        try:
            invite = UserInvite.objects.get(
                pk=pk,
                accepted_at__isnull=True,
                cancelled_at__isnull=True,
            )
        except UserInvite.DoesNotExist:
            return Response({"detail": "Invite not found or already resolved."}, status=status.HTTP_404_NOT_FOUND)
        invite.cancelled_at = timezone.now()
        invite.save(update_fields=["cancelled_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class InviteUserView(APIView):
    """Send an invite to a new user (admin only)."""
    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = InviteUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].strip().lower()
        role = serializer.validated_data["role"]
        first_name = serializer.validated_data.get("first_name", "")

        # Only block if an active user holds this email. Soft-deleted users are
        # renamed when the invite is accepted, so they should not block new invites.
        if User.objects.filter(email=email, is_active=True).exists():
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

            sender_name = request.user.full_name
            greeting_line = f"Hi {first_name}," if first_name else "Hi there,"
            role_display = role.capitalize()

            # Plain-text fallback
            body = (
                f"{greeting_line}\n\n"
                f"{sender_name} has invited you to join Klikk as a {role_display}.\n\n"
                f"Accept your invitation here:\n{invite_url}\n\n"
                f"If you weren't expecting this, you can safely ignore this email.\n\n"
                f"— The Klikk Team"
            )

            html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1.0" />
</head>
<body style="margin:0;padding:0;background-color:#F0F0F8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
    <tr>
      <td align="center" style="padding:40px 16px 48px;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:560px;">

          <!-- Wordmark -->
          <tr>
            <td align="center" style="padding-bottom:28px;">
              <span style="font-size:30px;font-weight:800;color:#2B2D6E;letter-spacing:-0.5px;">Klikk<span style="color:#FF3D7F;">.</span></span>
            </td>
          </tr>

          <!-- Card -->
          <tr>
            <td style="background:#ffffff;border-radius:20px;overflow:hidden;box-shadow:0 4px 24px rgba(43,45,110,0.10);">

              <!-- Card header -->
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                <tr>
                  <td style="background:#2B2D6E;padding:36px 40px 32px;">
                    <p style="margin:0 0 6px;font-size:12px;font-weight:600;color:rgba(255,255,255,0.5);text-transform:uppercase;letter-spacing:0.1em;">You're invited</p>
                    <h1 style="margin:0;font-size:28px;font-weight:700;color:#ffffff;line-height:1.25;">{greeting_line}</h1>
                  </td>
                </tr>
              </table>

              <!-- Card body -->
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                <tr>
                  <td style="padding:32px 40px 0;">

                    <!-- Role pill -->
                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin-bottom:24px;">
                      <tr>
                        <td style="background:#EEF0FA;border-radius:100px;padding:6px 18px;">
                          <span style="font-size:13px;font-weight:600;color:#2B2D6E;">{role_display}</span>
                        </td>
                      </tr>
                    </table>

                    <p style="margin:0 0 8px;font-size:16px;color:#374151;line-height:1.6;">
                      <strong style="color:#111827;">{sender_name}</strong> has invited you to join <strong style="color:#2B2D6E;">Klikk</strong> — South Africa's smart property management platform.
                    </p>
                    <p style="margin:0 0 32px;font-size:15px;color:#6B7280;line-height:1.6;">
                      Click the button below to create your account and get started.
                    </p>

                    <!-- CTA button -->
                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin-bottom:32px;">
                      <tr>
                        <td style="border-radius:10px;background:#2B2D6E;">
                          <a href="{invite_url}" target="_blank"
                             style="display:inline-block;padding:15px 36px;font-size:16px;font-weight:600;color:#ffffff;text-decoration:none;border-radius:10px;letter-spacing:0.01em;">
                            Accept Invitation &rarr;
                          </a>
                        </td>
                      </tr>
                    </table>

                    <!-- Fallback link -->
                    <p style="margin:0 0 8px;font-size:13px;color:#9CA3AF;">Or copy and paste this link into your browser:</p>
                    <p style="margin:0;font-size:12px;color:#2B2D6E;word-break:break-all;background:#F8F8FC;border:1px solid #E5E5F0;border-radius:8px;padding:12px 14px;">{invite_url}</p>

                  </td>
                </tr>
              </table>

              <!-- Card footer -->
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                <tr>
                  <td style="padding:28px 40px 32px;margin-top:8px;border-top:1px solid #F3F4F6;margin:24px 40px 0;">
                    <p style="margin:0;font-size:13px;color:#9CA3AF;line-height:1.6;">
                      This invitation was sent by <strong style="color:#6B7280;">{sender_name}</strong> via Klikk.<br />
                      If you weren't expecting this, you can safely ignore this email.
                    </p>
                  </td>
                </tr>
              </table>

            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td align="center" style="padding:28px 0 0;">
              <p style="margin:0;font-size:12px;color:#9CA3AF;">&copy; 2025 Klikk &middot; All rights reserved</p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

            send_email(
                subject=f"{sender_name} invited you to join Klikk",
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
         Accessible to any authenticated agent/admin (needed for isAgency check).
    PUT  → create-or-update (upsert) the Agency record. Admin only.
    Supports multipart/form-data for logo uploads.
    """
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAgentOrAdmin()]
        return [IsAdmin()]

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
