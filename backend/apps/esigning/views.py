import logging
from rest_framework.views import APIView
from rest_framework.generics import ListCreateAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import ESigningSubmission
from .serializers import ESigningSubmissionSerializer
from . import services

logger = logging.getLogger(__name__)


class ESigningSubmissionListCreateView(ListCreateAPIView):
    serializer_class = ESigningSubmissionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = ESigningSubmission.objects.select_related('lease__unit__property')
        lease_id = self.request.query_params.get('lease_id')
        if lease_id:
            qs = qs.filter(lease_id=lease_id)
        return qs

    def create(self, request, *args, **kwargs):
        from apps.leases.models import Lease
        lease_id = request.data.get('lease_id')
        signers  = request.data.get('signers', [])

        if not lease_id:
            return Response({'error': 'lease_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not signers:
            return Response({'error': 'At least one signer is required'}, status=status.HTTP_400_BAD_REQUEST)

        lease = get_object_or_404(Lease, pk=lease_id)

        try:
            result = services.create_lease_submission(lease, signers)
        except Exception as e:
            logger.exception("DocuSeal submission failed")
            return Response({'error': str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        template_data = result['template']
        submission_list = result['submission']

        if isinstance(submission_list, list) and submission_list:
            first = submission_list[0]
            submission_id = first.get('submission_id') or first.get('id', '')
        else:
            submission_id = ''

        signer_records = []
        for item in (submission_list if isinstance(submission_list, list) else [submission_list]):
            signer_records.append({
                'id':           item.get('id'),
                'name':         item.get('name', ''),
                'email':        item.get('email', ''),
                'role':         item.get('role', ''),
                'status':       item.get('status', 'sent'),
                'slug':         item.get('slug', ''),
                'embed_src':    item.get('embed_src', ''),
                'completed_at': item.get('completed_at'),
            })

        obj = ESigningSubmission.objects.create(
            lease=lease,
            docuseal_submission_id=str(submission_id),
            docuseal_template_id=str(template_data.get('id', '')),
            status=ESigningSubmission.Status.PENDING,
            signers=signer_records,
            created_by=request.user,
        )

        return Response(ESigningSubmissionSerializer(obj).data, status=status.HTTP_201_CREATED)


class ESigningSubmissionDetailView(RetrieveAPIView):
    serializer_class = ESigningSubmissionSerializer
    permission_classes = [IsAuthenticated]
    queryset = ESigningSubmission.objects.select_related('lease__unit__property')


class ESigningResendView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        from django.conf import settings
        import requests as req
        obj = get_object_or_404(ESigningSubmission, pk=pk)
        submitter_id = request.data.get('submitter_id')
        if not submitter_id:
            return Response({'error': 'submitter_id required'}, status=status.HTTP_400_BAD_REQUEST)

        api_url = getattr(settings, 'DOCUSEAL_API_URL', 'https://api.docuseal.com')
        api_key = getattr(settings, 'DOCUSEAL_API_KEY', '')
        try:
            r = req.post(
                f"{api_url.rstrip('/')}/api/submitters/{submitter_id}/send_email",
                headers={'X-Auth-Token': api_key, 'Content-Type': 'application/json'},
                timeout=15,
            )
            r.raise_for_status()
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({'ok': True})
