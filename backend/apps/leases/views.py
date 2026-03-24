from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Lease, LeaseDocument
from .serializers import LeaseSerializer, LeaseDocumentSerializer


class LeaseViewSet(viewsets.ModelViewSet):
    serializer_class = LeaseSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["status", "unit"]

    def get_queryset(self):
        user = self.request.user
        if user.role == "tenant" and hasattr(user, "person_profile"):
            person = user.person_profile
            return Lease.objects.filter(primary_tenant=person).select_related(
                "unit__property", "primary_tenant"
            )
        return Lease.objects.all().select_related("unit__property", "primary_tenant")

    @action(detail=True, methods=["get", "post"], url_path="documents")
    def documents(self, request, pk=None):
        lease = self.get_object()
        if request.method == "GET":
            docs = lease.documents.all()
            serializer = LeaseDocumentSerializer(docs, many=True, context={"request": request})
            return Response(serializer.data)

        serializer = LeaseDocumentSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save(lease=lease)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
