from rest_framework import serializers
from .models import ESigningSubmission


class ESigningSubmissionSerializer(serializers.ModelSerializer):
    lease_label = serializers.SerializerMethodField()

    class Meta:
        model = ESigningSubmission
        fields = [
            'id', 'lease', 'lease_label', 'docuseal_submission_id', 'docuseal_template_id',
            'status', 'signers', 'signed_pdf_url', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'docuseal_submission_id', 'docuseal_template_id', 'status',
            'signers', 'signed_pdf_url', 'created_at', 'updated_at',
        ]

    def get_lease_label(self, obj):
        return f"{obj.lease.unit.property.name} — Unit {obj.lease.unit.unit_number}"
