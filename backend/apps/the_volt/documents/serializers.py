from rest_framework import serializers

from .models import VaultDocument, DocumentVersion


class DocumentVersionSerializer(serializers.ModelSerializer):
    """Serializer for a single document version. No file field in output — use download endpoint."""

    class Meta:
        model = DocumentVersion
        fields = [
            "id",
            "document_id",
            "version_number",
            "original_filename",
            "file_size_bytes",
            "sha256_hash",
            "mime_type",
            "notes",
            "chroma_id",
            "extracted_data",
            "uploaded_at",
        ]
        read_only_fields = fields


class VaultDocumentSerializer(serializers.ModelSerializer):
    current_version = DocumentVersionSerializer(read_only=True)
    versions_count = serializers.SerializerMethodField()
    document_type_display = serializers.CharField(source="get_document_type_display", read_only=True)

    class Meta:
        model = VaultDocument
        fields = [
            "id",
            "entity_id",
            "document_type",
            "document_type_display",
            "label",
            "current_version",
            "versions_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "current_version", "versions_count", "created_at", "updated_at"]

    def get_versions_count(self, obj):
        return obj.versions.count()


class DocumentUploadSerializer(serializers.Serializer):
    """Used for POST /documents/{id}/versions/ (multipart upload).

    The client is responsible for OCR / structured extraction. Pass the parsed
    representation in `extracted_data` — this is what gets indexed into ChromaDB.
    The server does NOT re-OCR the file.
    """
    file = serializers.FileField()
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    extracted_data = serializers.JSONField(
        required=False,
        default=dict,
        help_text="Client-supplied OCR/structured JSON of the document content.",
    )

    def to_internal_value(self, data):
        # extracted_data may arrive as a JSON string in multipart requests
        import json
        if hasattr(data, "copy"):
            data = data.copy()
        raw = data.get("extracted_data") if hasattr(data, "get") else None
        if isinstance(raw, str) and raw.strip():
            try:
                data["extracted_data"] = json.loads(raw)
            except json.JSONDecodeError:
                raise serializers.ValidationError({"extracted_data": "Must be valid JSON."})
        return super().to_internal_value(data)
