import io
import re
import base64
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

DOCUSEAL_API_URL = getattr(settings, 'DOCUSEAL_API_URL', 'https://api.docuseal.com')
DOCUSEAL_API_KEY = getattr(settings, 'DOCUSEAL_API_KEY', '')


def _headers():
    return {'X-Auth-Token': DOCUSEAL_API_KEY, 'Content-Type': 'application/json'}


def _docuseal_post(path, payload):
    url = f"{DOCUSEAL_API_URL.rstrip('/')}{path}"
    resp = requests.post(url, headers=_headers(), json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def upload_pdf_template(pdf_bytes: bytes, name: str) -> dict:
    """Upload a PDF to DocuSeal and get back a template dict."""
    b64 = base64.b64encode(pdf_bytes).decode()
    return _docuseal_post('/api/templates', {
        'name': name,
        'documents': [{'name': f'{name}.pdf', 'file': b64}],
    })


def create_submission(template_id: int, submitters: list) -> dict:
    """
    Create a DocuSeal submission.
    submitters = [{'name': '...', 'email': '...', 'role': '...', 'send_email': True}]
    Returns the submissions list from DocuSeal.
    """
    return _docuseal_post('/api/submissions', {
        'template_id': template_id,
        'submitters': submitters,
    })


def build_lease_context(lease) -> dict:
    """Map a Lease ORM object to merge-field key/value pairs."""
    unit = lease.unit
    prop = unit.property
    tenant = lease.primary_tenant

    ctx = {
        'landlord_name':    getattr(prop, 'owner', None) and prop.owner.full_name or '—',
        'property_address': prop.address or '—',
        'property_name':    prop.name or '—',
        'unit_number':      unit.unit_number,
        'city':             getattr(prop, 'city', '') or '—',
        'province':         getattr(prop, 'province', '') or '—',
        'tenant_name':      tenant.full_name if tenant else '—',
        'tenant_id':        tenant.id_number if tenant else '—',
        'tenant_phone':     tenant.phone if tenant else '—',
        'tenant_email':     tenant.email if tenant else '—',
        'lease_start':      str(lease.start_date),
        'lease_end':        str(lease.end_date),
        'monthly_rent':     f'R {lease.monthly_rent:,.2f}',
        'deposit':          f'R {lease.deposit:,.2f}',
        'notice_period_days': str(getattr(lease, 'notice_period_days', 30)),
        'water_included':   'Included' if getattr(lease, 'water_included', True) else 'Excluded',
        'electricity_prepaid': 'Prepaid' if getattr(lease, 'electricity_prepaid', True) else 'Included in rent',
        'max_occupants':    str(getattr(lease, 'max_occupants', 1)),
        'payment_reference': getattr(lease, 'payment_reference', '') or '—',
    }
    co = list(lease.co_tenants.select_related('person').all())
    ctx['co_tenants'] = ', '.join(ct.person.full_name for ct in co if ct.person.full_name) or '—'
    return ctx


def generate_lease_pdf(lease) -> bytes:
    """
    Generate a filled PDF for the lease.
    Uses the first active LeaseTemplate; falls back to a plain-text layout.
    Returns PDF bytes.
    """
    from apps.leases.models import LeaseTemplate
    from xhtml2pdf import pisa

    ctx = build_lease_context(lease)
    tmpl = LeaseTemplate.objects.filter(is_active=True).first()

    if tmpl and tmpl.content_html:
        html_body = tmpl.content_html

        def replace_field(m):
            field = m.group(1)
            val = ctx.get(field, f'{{ {field} }}')
            return f'<span class="filled">{val}</span>'

        html_body = re.sub(
            r'<span[^>]+data-merge-field="([^"]+)"[^>]*>.*?</span>',
            replace_field, html_body, flags=re.DOTALL
        )
        html_body = re.sub(
            r'\{\{\s*(\w+)\s*\}\}',
            lambda m: ctx.get(m.group(1), m.group(0)),
            html_body
        )
        html_body = re.sub(
            r'<div[^>]+data-page-break[^>]*>.*?</div>',
            '<div style="page-break-after:always;"></div>',
            html_body, flags=re.DOTALL
        )
    else:
        rows = ''.join(
            f'<tr><td>{k.replace("_", " ").title()}</td><td>{v}</td></tr>'
            for k, v in ctx.items()
        )
        html_body = (
            f'<h1>Lease Agreement</h1>'
            f'<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">'
            f'{rows}</table>'
        )

    css = """
        @page { size: A4; margin: 2cm; }
        body { font-family: Arial, sans-serif; font-size: 10.5pt; line-height: 1.55; color: #111; }
        h1 { font-size: 14pt; font-weight: bold; text-align: center; margin-bottom: 12pt; }
        h2 { font-size: 11pt; font-weight: bold; margin: 8pt 0 3pt; }
        p, li { margin: 3pt 0; }
        table { border-collapse: collapse; width: 100%; margin: 4pt 0; }
        td, th { border: 1px solid #d1d5db; padding: 5pt 7pt; font-size: 10pt; }
        .filled { font-weight: 600; }
    """
    full_html = (
        '<!DOCTYPE html><html><head><meta charset="UTF-8">'
        f'<style>{css}</style></head><body>{html_body}</body></html>'
    )
    buf = io.BytesIO()
    result = pisa.CreatePDF(full_html, dest=buf)
    if result.err:
        raise RuntimeError("PDF generation failed")
    buf.seek(0)
    return buf.read()


def create_lease_submission(lease, signers: list) -> dict:
    """
    High-level function:
    1. Generate lease PDF
    2. Upload to DocuSeal as template
    3. Create submission with given signers
    Returns {'template': {...}, 'submission': [...]}
    """
    pdf_bytes = generate_lease_pdf(lease)
    tenant_name = lease.primary_tenant.full_name if lease.primary_tenant else 'Tenant'
    name = f"Lease - {tenant_name} - {lease.unit.property.name} Unit {lease.unit.unit_number}"

    template_data = upload_pdf_template(pdf_bytes, name)
    template_id = template_data['id']

    submission_data = create_submission(template_id, [
        {
            'name': s['name'],
            'email': s['email'],
            'role': s.get('role', 'Signer'),
            'send_email': s.get('send_email', True),
        }
        for s in signers
    ])

    return {'template': template_data, 'submission': submission_data}
