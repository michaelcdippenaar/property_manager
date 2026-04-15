from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.the_volt.owners.models import VaultOwner
from apps.the_volt.owners.serializers import VaultOwnerSerializer


class VaultOwnerMeView(APIView):
    """GET — return (or create) the vault for the authenticated user."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        owner = VaultOwner.get_or_create_for_user(request.user)
        return Response(VaultOwnerSerializer(owner).data)
