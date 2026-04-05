from rest_framework import serializers
from .models import ESigningSubmission


class ESigningSubmissionSerializer(serializers.ModelSerializer):
    lease_label = serializers.SerializerMethodField()
    current_signer = serializers.SerializerMethodField()
    signing_progress = serializers.SerializerMethodField()

    class Meta:
        model = ESigningSubmission
        fields = [
            'id', 'lease', 'lease_label',
            'status', 'signing_mode', 'signing_backend', 'signers',
            'captured_data', 'created_at', 'updated_at',
            'current_signer', 'signing_progress',
        ]
        read_only_fields = [
            'status', 'signers', 'created_at', 'updated_at',
        ]

    def get_lease_label(self, obj):
        return f"{obj.lease.unit.property.name} — Unit {obj.lease.unit.unit_number}"

    def get_current_signer(self, obj):
        """Return the signer whose turn it is (sequential) or None."""
        if obj.status in ('completed', 'declined'):
            return None
        for s in obj.signers or []:
            st = (s.get('status') or '').lower()
            if st not in ('completed', 'signed', 'declined'):
                return {
                    'id': s.get('id'),
                    'name': s.get('name', ''),
                    'email': s.get('email', ''),
                    'role': s.get('role', ''),
                    'status': s.get('status', ''),
                    'order': s.get('order', 0),
                }
        return None

    def get_signing_progress(self, obj):
        """Return signing progress summary."""
        signers = obj.signers or []
        total = len(signers)
        completed = sum(
            1 for s in signers
            if (s.get('status') or '').lower() in ('completed', 'signed')
        )
        declined = sum(
            1 for s in signers
            if (s.get('status') or '').lower() == 'declined'
        )
        return {
            'total': total,
            'completed': completed,
            'declined': declined,
            'pending': total - completed - declined,
        }
