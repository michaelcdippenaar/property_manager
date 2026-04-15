import logging
import mimetypes

from django.core.files.base import ContentFile
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.the_volt.owners.models import VaultOwner
from apps.the_volt.encryption.utils import encrypt_bytes, decrypt_bytes, hash_bytes
from .models import VaultDocument, DocumentVersion
from .serializers import VaultDocumentSerializer, DocumentVersionSerializer, DocumentUploadSerializer

logger = logging.getLogger(__name__)


class VaultDocumentViewSet(viewsets.ModelViewSet):
    """CRUD for vault documents (document groups + version uploads)."""

    serializer_class = VaultDocumentSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["entity_id", "document_type"]

    def get_queryset(self):
        return VaultDocument.objects.filter(
            entity__vault__user=self.request.user,
        ).select_related("entity__vault", "current_version")

    def perform_create(self, serializer):
        # Verify entity belongs to user's vault
        entity = serializer.validated_data.get("entity")
        if entity and entity.vault.user != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Entity does not belong to your vault.")
        serializer.save()

    # -----------------------------------------------------------------------
    # Version management
    # -----------------------------------------------------------------------

    @action(detail=True, methods=["get"], url_path="versions")
    def list_versions(self, request, pk=None):
        """List all versions for this document."""
        document = self.get_object()
        versions = document.versions.all()
        return Response(DocumentVersionSerializer(versions, many=True).data)

    @action(detail=True, methods=["post"], url_path="versions", url_name="upload-version")
    def upload_version(self, request, pk=None):
        """Upload a new version of this document.

        Accepts multipart/form-data with a 'file' field.
        Encrypts the file before writing to disk.
        Signal fires post-save to update current_version and trigger ChromaDB ingestion.
        """
        document = self.get_object()
        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data["file"]
        notes = serializer.validated_data.get("notes", "")
        extracted_data = serializer.validated_data.get("extracted_data") or {}

        # Read plaintext bytes
        plaintext_bytes = uploaded_file.read()
        original_filename = uploaded_file.name
        file_size = len(plaintext_bytes)

        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(original_filename)
        mime_type = mime_type or "application/octet-stream"

        # Hash plaintext (tamper detection)
        sha256 = hash_bytes(plaintext_bytes)

        # Encrypt
        owner_id = document.entity.vault_id
        encrypted_bytes = encrypt_bytes(plaintext_bytes, owner_id)

        # Determine version number (save() override does this, but we need it for the upload path)
        next_version = document.versions.count() + 1

        # Create version instance (without file first to get version_number set)
        version = DocumentVersion(
            document=document,
            version_number=next_version,
            original_filename=original_filename,
            file_size_bytes=file_size,
            sha256_hash=sha256,
            mime_type=mime_type,
            notes=notes,
            extracted_data=extracted_data,
        )
        # Save encrypted bytes as file (upload_to uses version_number which is already set)
        version.file.save(
            f"{next_version}.enc",
            ContentFile(encrypted_bytes),
            save=False,
        )
        version.save()  # triggers post_save signal → current_version update + ChromaDB

        return Response(DocumentVersionSerializer(version).data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["get"],
        url_path=r"versions/(?P<vid>[0-9]+)/download",
        url_name="download-version",
    )
    def download_version(self, request, pk=None, vid=None):
        """Decrypt and stream a specific document version.

        Returns the plaintext file with the original filename.
        """
        document = self.get_object()
        try:
            version = document.versions.get(version_number=int(vid))
        except DocumentVersion.DoesNotExist:
            return Response({"detail": "Version not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            owner_id = document.entity.vault_id
            version.file.seek(0)
            encrypted_bytes = version.file.read()
            plaintext_bytes = decrypt_bytes(encrypted_bytes, owner_id)
        except Exception:
            logger.exception(
                "Volt: failed to decrypt version_id=%s for document_id=%s", version.pk, document.pk
            )
            return Response({"detail": "Decryption failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        response = HttpResponse(plaintext_bytes, content_type=version.mime_type or "application/octet-stream")
        response["Content-Disposition"] = f'attachment; filename="{version.original_filename}"'
        response["X-Vault-SHA256"] = version.sha256_hash
        return response
