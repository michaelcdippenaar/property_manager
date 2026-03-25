import hashlib
import hmac
import json
import logging
from django.conf import settings
from django.http import HttpResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .models import ESigningSubmission

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class DocuSealWebhookView(View):
    """
    POST /api/v1/esigning/webhook/
    DocuSeal sends events here. We update submission status accordingly.
    Optionally verifies HMAC if DOCUSEAL_WEBHOOK_SECRET is set.
    """

    def post(self, request):
        secret = getattr(settings, 'DOCUSEAL_WEBHOOK_SECRET', '')
        if secret:
            sig = request.headers.get('X-Docuseal-Signature', '')
            expected = hmac.new(secret.encode(), request.body, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(sig, expected):
                return HttpResponse('Invalid signature', status=400)

        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return HttpResponse('Bad JSON', status=400)

        event_type = payload.get('event_type', '')
        data       = payload.get('data', {})

        logger.info("DocuSeal webhook: %s", event_type)

        submission_id = (
            data.get('submission_id') or
            data.get('submission', {}).get('id') or
            data.get('id', '')
        )
        if not submission_id:
            return HttpResponse('ok')

        try:
            obj = ESigningSubmission.objects.get(docuseal_submission_id=str(submission_id))
        except ESigningSubmission.DoesNotExist:
            return HttpResponse('ok')

        obj.webhook_payload = payload

        if event_type in ('submission.completed', 'form.completed'):
            obj.status = ESigningSubmission.Status.COMPLETED
            signed_url = data.get('audit_log_url') or data.get('documents', [{}])[0].get('url', '')
            if signed_url:
                obj.signed_pdf_url = signed_url

            submitters = data.get('submitters', [])
            updated_signers = []
            for s in obj.signers:
                matching = next(
                    (x for x in submitters if str(x.get('id')) == str(s.get('id'))),
                    None
                )
                if matching:
                    s = {
                        **s,
                        'status': matching.get('status', s.get('status')),
                        'completed_at': matching.get('completed_at'),
                    }
                updated_signers.append(s)
            if updated_signers:
                obj.signers = updated_signers

        elif event_type == 'submission.declined':
            obj.status = ESigningSubmission.Status.DECLINED

        elif event_type in ('form.viewed', 'form.started'):
            if obj.status == ESigningSubmission.Status.PENDING:
                obj.status = ESigningSubmission.Status.IN_PROGRESS

        obj.save()
        return HttpResponse('ok')
