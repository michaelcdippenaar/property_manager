import hashlib
import re
import logging
import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def _docuseal_headers():
    key = (getattr(settings, 'DOCUSEAL_API_KEY', '') or '').strip()
    if not key:
        raise ValueError(
            'DOCUSEAL_API_KEY is empty. Set it in backend/.env to the API token from your DocuSeal '
            'instance (same token that works in Postman), then restart Django.'
        )
    return {'X-Auth-Token': key, 'Content-Type': 'application/json'}


def _docuseal_base():
    return getattr(settings, 'DOCUSEAL_API_URL', 'https://api.docuseal.com').rstrip('/')


def _docuseal_post(path, payload, *, timeout=30):
    url = f"{_docuseal_base()}{path}"
    resp = requests.post(url, headers=_docuseal_headers(), json=payload, timeout=timeout)
    if not resp.ok:
        body = (resp.text or '')[:2000]
        logger.error('DocuSeal API error %s %s — %s', resp.status_code, url, body)
    resp.raise_for_status()
    return resp.json()


def _docuseal_get(path, *, timeout=15):
    url = f"{_docuseal_base()}{path}"
    resp = requests.get(url, headers=_docuseal_headers(), timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _docuseal_put(path, payload, *, timeout=30):
    url = f"{_docuseal_base()}{path}"
    resp = requests.put(url, headers=_docuseal_headers(), json=payload, timeout=timeout)
    if not resp.ok:
        body = (resp.text or '')[:2000]
        logger.error('DocuSeal API error %s %s — %s', resp.status_code, url, body)
    resp.raise_for_status()
    return resp.json()


def get_submitter(submitter_id: int) -> dict:
    """Fetch submitter details from DocuSeal (includes documents, status)."""
    return _docuseal_get(f'/submitters/{submitter_id}')


def get_template_fields(template_id: int) -> dict:
    """Fetch template details including field definitions and positions."""
    return _docuseal_get(f'/templates/{template_id}')


def submit_signature(submitter_id: int, fields: list) -> dict:
    """
    Submit signature data to DocuSeal and mark the submitter as completed.

    fields = [
        {'name': 'Signature (First Party)', 'default_value': 'data:image/png;base64,...'},
        {'name': 'Date (First Party)', 'default_value': '2026-03-26'},
    ]
    """
    return _docuseal_put(f'/submitters/{submitter_id}', {
        'completed': True,
        'fields': fields,
    })


def get_document_pdf_url(submitter_id: int) -> str | None:
    """
    Get the PDF URL for a submitter's document from DocuSeal.

    Tries multiple sources in order:
    1. Submitter's own documents (post-signing — signed copy attached)
    2. Submission documents via GET /submissions/{id}/documents
       (works for submissions created via POST /submissions/html)
    3. Template documents (for submissions created via POST /submissions)
    """
    data = get_submitter(submitter_id)

    # 1. Signed document already attached to submitter (post-signing)
    docs = data.get('documents') or []
    if docs:
        return docs[0].get('url')

    # 2. Submission documents (pre-signing — works for /submissions/html)
    submission_id = data.get('submission_id')
    if submission_id:
        try:
            sub_docs = _docuseal_get(f'/submissions/{submission_id}/documents')
            doc_list = sub_docs.get('documents') or []
            if doc_list:
                return doc_list[0].get('url')
        except Exception:
            logger.debug('Could not fetch submission %s documents', submission_id)

    # 3. Fall back to the template PDF (for template-based submissions)
    template = data.get('template') or {}
    template_id = template.get('id')
    if template_id:
        try:
            tmpl = get_template_fields(int(template_id))
            tmpl_docs = tmpl.get('documents') or []
            if tmpl_docs:
                return tmpl_docs[0].get('url')
        except Exception:
            logger.debug('Could not fetch template %s documents', template_id)

    return None


def _extract_template_fields(content_html: str) -> list:
    """Extract the signing fields array from a v1 JSON template content."""
    import json
    raw = (content_html or '').strip()
    if not raw or not raw.startswith('{'):
        return []
    try:
        doc = json.loads(raw)
        if isinstance(doc, dict) and doc.get('v') in (1, 2):
            return doc.get('fields', [])
    except (json.JSONDecodeError, TypeError):
        pass
    return []



def create_submission(
    template_id: int,
    submitters: list,
    send_email: bool = True,
    order: str = 'random',
) -> dict:
    """
    Create a DocuSeal submission.
    submitters = [{'name': '...', 'email': '...', 'role': '...', 'send_email': True, 'order': 0}]

    order: 'preserved' for sequential signing (respects per-submitter order values),
           'random' for parallel (everyone signs at once, default).

    Returns the submissions list from DocuSeal.
    """
    return _docuseal_post('/submissions', {
        'template_id': template_id,
        'send_email': send_email,
        'order': order,
        'submitters': submitters,
    })


def _roles_from_template(template_data: dict) -> list[str]:
    """DocuSeal `role` on each submitter must match `submitters[].name` on the template."""
    subs = template_data.get('submitters') or []
    roles = [s.get('name') for s in subs if s.get('name')]
    return [r for r in roles if r]


def _get_landlord_info(lease) -> dict | None:
    """Resolve landlord name/email/phone from Landlord → PropertyOwnership → Property.owner."""
    prop = lease.unit.property
    ownership = None
    try:
        ownership = prop.ownerships.filter(is_current=True).select_related('landlord').first()
    except Exception:
        pass

    if ownership:
        # Prefer linked Landlord entity
        ll = getattr(ownership, 'landlord', None)
        if ll:
            name = ll.representative_name or ll.name
            email = ll.representative_email or ll.email
            phone = ll.representative_phone or ll.phone
            if email:
                return {'name': name or '', 'email': email, 'phone': phone or '', 'landlord_id': ll.pk}

        # Fallback to denormalized fields on PropertyOwnership
        name = ownership.representative_name or ownership.owner_name
        email = ownership.representative_email or ownership.owner_email
        phone = ownership.representative_phone or ownership.owner_phone
        if email:
            return {'name': name or '', 'email': email, 'phone': phone or ''}

    # Fallback: Property.owner (Person FK)
    owner_person = getattr(prop, 'owner', None)
    if owner_person:
        email = getattr(owner_person, 'email', '') or ''
        if email:
            return {'name': getattr(owner_person, 'full_name', '') or '', 'email': email, 'phone': getattr(owner_person, 'phone', '') or ''}

    return None


def build_lease_context(lease) -> dict:
    """Map a Lease ORM object to merge-field key/value pairs."""
    unit = lease.unit
    prop = unit.property
    tenant = lease.primary_tenant

    # Resolve landlord info: try current PropertyOwnership first, then Property.owner (Person)
    owner_person = getattr(prop, 'owner', None)
    ownership = None
    try:
        ownership = prop.ownerships.filter(is_current=True).first()
    except Exception:
        pass

    landlord_name = '—'
    landlord_contact = '—'
    landlord_email = '—'
    landlord_id = '—'

    if ownership:
        landlord_name = ownership.representative_name or ownership.owner_name or '—'
        landlord_contact = ownership.representative_phone or ownership.owner_phone or '—'
        landlord_email = ownership.representative_email or ownership.owner_email or '—'
        landlord_id = ownership.representative_id_number or ownership.registration_number or '—'
    elif owner_person:
        landlord_name = owner_person.full_name or '—'
        landlord_contact = getattr(owner_person, 'phone', '') or '—'
        landlord_email = getattr(owner_person, 'email', '') or '—'
        landlord_id = getattr(owner_person, 'id_number', '') or '—'

    ctx = {
        # ── Landlord / Property ──────────────────────────────────
        'landlord_name':    landlord_name,
        'landlord_contact': landlord_contact,
        'landlord_phone':   landlord_contact,      # alias
        'landlord_email':   landlord_email,
        'landlord_id':      landlord_id,
        'property_address': prop.address or '—',
        'property_name':    prop.name or '—',
        'unit_number':      unit.unit_number,
        'city':             getattr(prop, 'city', '') or '—',
        'province':         getattr(prop, 'province', '') or '—',

        # ── Primary tenant (legacy names) ────────────────────────
        'tenant_name':      tenant.full_name if tenant else '—',
        'tenant_id':        tenant.id_number if tenant else '—',
        'tenant_phone':     tenant.phone if tenant else '—',
        'tenant_email':     tenant.email if tenant else '—',
        'tenant_contact':   (tenant.phone if tenant else '') or '—',   # alias
        'tenant_address':   (tenant.address if tenant else '') or '—',
        'tenant_employer':  (tenant.employer if tenant else '') or '—',
        'tenant_occupation': (tenant.occupation if tenant else '') or '—',
        'tenant_dob':       str(tenant.date_of_birth) if tenant and tenant.date_of_birth else '—',
        'tenant_emergency_contact': (tenant.emergency_contact_name if tenant else '') or '—',
        'tenant_emergency_phone':   (tenant.emergency_contact_phone if tenant else '') or '—',

        # ── Primary tenant (numbered aliases: tenant_1_*) ────────
        'tenant_1_name':    tenant.full_name if tenant else '—',
        'tenant_1_id':      tenant.id_number if tenant else '—',
        'tenant_1_phone':   tenant.phone if tenant else '—',
        'tenant_1_email':   tenant.email if tenant else '—',
        'tenant_1_address': (tenant.address if tenant else '') or '—',
        'tenant_1_employer': (tenant.employer if tenant else '') or '—',
        'tenant_1_occupation': (tenant.occupation if tenant else '') or '—',
        'tenant_1_dob':     str(tenant.date_of_birth) if tenant and tenant.date_of_birth else '—',
        'tenant_1_emergency_contact': (tenant.emergency_contact_name if tenant else '') or '—',
        'tenant_1_emergency_phone':   (tenant.emergency_contact_phone if tenant else '') or '—',

        # ── Lease terms ──────────────────────────────────────────
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

    # ── Co-tenants: tenant_2_*, tenant_3_* ───────────────────────
    co = list(lease.co_tenants.select_related('person').all())
    ctx['co_tenants'] = ', '.join(ct.person.full_name for ct in co if ct.person.full_name) or '—'

    for i, ct in enumerate(co[:3], start=2):       # up to 3 co-tenants
        p = ct.person
        ctx[f'tenant_{i}_name']  = p.full_name or '—'
        ctx[f'tenant_{i}_id']    = p.id_number or '—'
        ctx[f'tenant_{i}_phone'] = p.phone or '—'
        ctx[f'tenant_{i}_email'] = p.email or '—'
        ctx[f'tenant_{i}_address'] = p.address or '—'
        ctx[f'tenant_{i}_employer'] = p.employer or '—'
        ctx[f'tenant_{i}_occupation'] = p.occupation or '—'
        ctx[f'tenant_{i}_dob'] = str(p.date_of_birth) if p.date_of_birth else '—'
        ctx[f'tenant_{i}_emergency_contact'] = p.emergency_contact_name or '—'
        ctx[f'tenant_{i}_emergency_phone'] = p.emergency_contact_phone or '—'

    # Fill any missing tenant slots with em-dash so templates don't
    # show raw {{ tenant_3_name }} when there's no third tenant.
    for i in range(2, 4):
        for suffix in ('name', 'id', 'phone', 'email', 'address', 'employer',
                        'occupation', 'dob', 'emergency_contact', 'emergency_phone'):
            ctx.setdefault(f'tenant_{i}_{suffix}', '—')

    # ── Occupants ────────────────────────────────────────────────
    occupants = list(lease.occupants.select_related('person').all())
    for i, occ in enumerate(occupants[:4], start=1):
        p = occ.person
        ctx[f'occupant_{i}_name'] = p.full_name or '—'
        ctx[f'occupant_{i}_id'] = p.id_number or '—'
        ctx[f'occupant_{i}_relationship'] = occ.relationship_to_tenant or '—'

    # Fill missing occupant slots
    for i in range(1, 5):
        for suffix in ('name', 'id', 'relationship'):
            ctx.setdefault(f'occupant_{i}_{suffix}', '—')

    return ctx


def _signing_role(party: str, num_signers: int) -> str:
    """Map a template field party to a DocuSeal signer role name."""
    roles = ['First Party'] + [f'Signer {i + 1}' for i in range(1, num_signers)]
    p = (party or '').lower()
    if 'landlord' in p or 'lessor' in p:
        return roles[0]
    if 'tenant' in p or 'lessee' in p:
        return roles[1] if len(roles) > 1 else roles[0]
    return roles[0]


def _docuseal_field_tag(field: dict, num_signers: int, *, block: bool = True) -> str:
    """Convert a template editor signing field to a DocuSeal HTML custom tag.

    DocuSeal recognises <signature-field>, <initials-field>, <date-field> etc.
    When block=True (default for template-positioned fields), the tag is wrapped
    in a <p> so it occupies its own line and doesn't overlap surrounding text.
    """
    ftype = (field.get('type') or '').lower()
    if ftype == 'initials':
        tag = 'initials-field'
        w, h = '100px', '40px'
    elif ftype == 'signature':
        tag = 'signature-field'
        w, h = '200px', '60px'
    else:
        return ''

    role = _signing_role(field.get('party', ''), num_signers)
    name = field.get('name', ftype)
    fmt_attr = ' format="drawn_or_typed"' if tag == 'signature-field' else ''
    inner = (
        f'<{tag} name="{name}" role="{role}" required="true"{fmt_attr} '
        f'style="width: {w}; height: {h}; display: inline-block;"> </{tag}>'
    )
    if block:
        return f'<p style="margin: 4pt 0;">{inner}</p>'
    return inner



def _map_signing_roles(html: str, num_signers: int) -> str:
    """Replace TipTap signer roles with DocuSeal role names in signing field tags.

    TipTap uses: landlord, tenant_1, tenant_2, witness_1, etc.
    DocuSeal uses: First Party, Signer 2, Signer 3, etc.
    """
    role_map: dict[str, str] = {
        'landlord': 'First Party',
        'lessor': 'First Party',
    }
    for i in range(1, max(num_signers, 4) + 1):
        ds_role = f'Signer {i + 1}' if (i + 1) <= num_signers else 'First Party'
        role_map[f'tenant_{i}'] = ds_role
        role_map[f'tenant'] = role_map.get('tenant', ds_role)  # bare "tenant" → first tenant role
    for i in range(1, 4):
        role_map[f'witness_{i}'] = f'Signer {num_signers + i}'

    def replace_role(m: re.Match) -> str:
        role = m.group(1)
        return f'role="{role_map.get(role, role)}"'

    # Only replace role attributes inside signing field tags
    return re.sub(
        r'(<(?:signature|initials|date)-field\b[^>]*?)role="([^"]+)"',
        lambda m: m.group(1) + f'role="{role_map.get(m.group(2), m.group(2))}"',
        html,
    )


def _deduplicate_field_names(html: str) -> str:
    """Ensure every signing field tag has a unique name attribute.

    DocuSeal deduplicates fields by name — repeated names are silently ignored.
    Appends an occurrence counter to make each field unique.
    """
    seen: dict[str, int] = {}

    def _make_unique(m: re.Match) -> str:
        full = m.group(0)
        name_match = re.search(r'name="([^"]+)"', full)
        if not name_match:
            return full
        name = name_match.group(1)
        seen[name] = seen.get(name, 0) + 1
        if seen[name] == 1:
            return full  # first occurrence unchanged
        unique = f'{name}_{seen[name]}'
        result = full.replace(f'name="{name}"', f'name="{unique}"', 1)
        # Also update data-field-name if present
        if f'data-field-name="{name}"' in result:
            result = result.replace(f'data-field-name="{name}"', f'data-field-name="{unique}"', 1)
        return result

    return re.sub(
        r'<(?:signature|initials|date)-field\b[^>]*>',
        _make_unique, html,
    )


def generate_lease_html(lease, num_signers: int = 1, template_id: int | None = None, native: bool = False) -> str:
    """
    Generate filled lease HTML ready for DocuSeal.

    TipTap editor outputs DocuSeal-native signing tags (<signature-field>,
    <initials-field>, <date-field>) directly via renderHTML(). This function:
    1. Extracts HTML from the v1/v2 JSON envelope
    2. Fills merge-field placeholders with lease data
    3. Maps TipTap signer roles to DocuSeal role names
    4. Appends a fallback signature page if no inline signing fields exist
    5. Wraps in an HTML5 document with CSS
    """
    from apps.leases.models import LeaseTemplate
    from apps.leases.template_views import _extract_html

    ctx = build_lease_context(lease)

    # Use specified template or fall back to most recent active one
    tmpl = None
    if template_id:
        tmpl = LeaseTemplate.objects.filter(pk=template_id).first()
    if not tmpl:
        tmpl = (
            LeaseTemplate.objects.filter(is_active=True).exclude(content_html='')
            .order_by('-id').first()
            or LeaseTemplate.objects.filter(is_active=True).order_by('-id').first()
        )

    if tmpl and tmpl.content_html:
        html_body = _extract_html(tmpl.content_html)

        # ── Replace merge field spans with filled values ──────────────
        def replace_field(m: re.Match) -> str:
            field = m.group(1)
            val = ctx.get(field)
            if val and val != '—':
                return f'<span style="font-weight:600">{val}</span>'
            if native:
                # Preserve as TipTap merge field node for editable input in signing view
                return (f'<span data-type="merge-field" class="merge-field" '
                        f'data-field-name="{field}">{{{{{field}}}}}</span>')
            val = ctx.get(field, f'{{ {field} }}')
            return f'<span style="font-weight:600">{val}</span>'

        # v1 format: <span data-merge-field="X">...</span>
        html_body = re.sub(
            r'<span[^>]+data-merge-field="([^"]+)"[^>]*>.*?</span>',
            replace_field, html_body, flags=re.DOTALL,
        )

        # v2 TipTap format: <span ... data-type="merge-field" ... data-field-name="X" ...>...</span>
        html_body = re.sub(
            r'<span[^>]+data-type="merge-field"[^>]+data-field-name="([^"]+)"[^>]*>.*?</span>',
            replace_field, html_body, flags=re.DOTALL,
        )

        # Also match reverse attribute order: data-field-name before data-type
        html_body = re.sub(
            r'<span[^>]+data-field-name="([^"]+)"[^>]+data-type="merge-field"[^>]*>.*?</span>',
            replace_field, html_body, flags=re.DOTALL,
        )

        # Remove legacy block field div placeholders from old editor
        html_body = re.sub(
            r'<div[^>]+data-field="[^"]*"[^>]+data-field-type="[^"]*"[^>]*>.*?</div>',
            '', html_body, flags=re.DOTALL,
        )

        # ── Convert legacy signature-block spans to DocuSeal native tags ─
        # Templates saved before the renderHTML change used:
        #   <span data-type="signature-block" data-field-name="X" data-field-type="signature"
        #         data-signer-role="landlord" ...>{{X}}</span>
        # Convert these to DocuSeal tags: <signature-field>, <initials-field>, <date-field>
        def _convert_legacy_signing_span(m: re.Match) -> str:
            attrs_str = m.group(1)
            field_type = re.search(r'data-field-type="([^"]+)"', attrs_str)
            field_name = re.search(r'data-field-name="([^"]+)"', attrs_str)
            signer_role = re.search(r'data-signer-role="([^"]+)"', attrs_str)

            ftype = field_type.group(1) if field_type else 'signature'
            fname = field_name.group(1) if field_name else ''
            role = signer_role.group(1) if signer_role else 'landlord'

            tag_map = {'signature': 'signature-field', 'initials': 'initials-field', 'date': 'date-field'}
            tag = tag_map.get(ftype, 'signature-field')

            dims = {'signature': 'width:200px;height:60px', 'initials': 'width:100px;height:40px',
                     'date': 'width:120px;height:24px'}.get(ftype, 'width:200px;height:60px')

            fmt = ' format="drawn_or_typed"' if ftype == 'signature' else ''
            return (f'<{tag} name="{fname}" role="{role}" required="true"{fmt} '
                    f'style="display:inline-block;{dims};margin:4px 6px;vertical-align:middle;"> </{tag}>')

        html_body = re.sub(
            r'<span([^>]+data-type="signature-block"[^>]*)>.*?</span>',
            _convert_legacy_signing_span, html_body, flags=re.DOTALL,
        )

        # ── Replace remaining {{field}} mustache markers ─────────────
        # Skip mustaches that are already inside a merge-field span (native mode
        # preserves them as TipTap nodes — we don't want to double-wrap).
        def replace_mustache(m: re.Match) -> str:
            field = m.group(1)
            # Check if this mustache is inside a merge-field span already
            start = m.start()
            preceding = html_body[max(0, start - 200):start]
            if 'data-field-name="' in preceding and '</span>' not in preceding.split('data-field-name="')[-1]:
                return m.group(0)  # leave as-is — already inside a merge field span
            val = ctx.get(field)
            if val and val != '—':
                return val
            if native:
                return (f'<span data-type="merge-field" class="merge-field" '
                        f'data-field-name="{field}">{{{{{field}}}}}</span>')
            return ctx.get(field, m.group(0))

        html_body = re.sub(r'\{\{\s*(\w+)\s*\}\}', replace_mustache, html_body)

        # ── Convert manual page breaks ────────────────────────────────
        html_body = re.sub(
            r'<div[^>]+data-page-break[^>]*>.*?</div>',
            '<div style="page-break-after:always;"></div>',
            html_body, flags=re.DOTALL,
        )

        # ── Map TipTap signer roles to DocuSeal roles (skip for native signing) ──
        if not native:
            html_body = _map_signing_roles(html_body, num_signers)

        # ── Deduplicate signing field names ──────────────────────────
        html_body = _deduplicate_field_names(html_body)

    else:
        # No template content — generate a simple table
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
        @page { size: A4; margin: 20mm 18mm 22mm 18mm; }
        body {
            font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
            font-size: 10.5pt; line-height: 1.6; color: #1a1a1a;
            margin: 0; padding: 0;
        }
        h1 { font-size: 15pt; font-weight: 700; text-align: center; margin: 0 0 6pt; letter-spacing: -0.01em; }
        h2 { font-size: 11.5pt; font-weight: 700; margin: 14pt 0 4pt; border-bottom: 0.5pt solid #d0d0d0; padding-bottom: 2pt; }
        h3 { font-size: 10.5pt; font-weight: 700; margin: 10pt 0 3pt; }
        p { margin: 3pt 0; orphans: 3; widows: 3; }
        li { margin: 2pt 0; }
        ul, ol { padding-left: 20pt; margin: 4pt 0; }
        table { border-collapse: collapse; width: 100%; margin: 6pt 0; page-break-inside: auto; }
        thead { display: table-header-group; }
        tr { page-break-inside: avoid; }
        td, th { border: 0.5pt solid #c0c0c0; padding: 5pt 7pt; font-size: 10pt; vertical-align: top; }
        th { background-color: #f5f5f5; font-weight: 600; text-align: left; }
    """

    return (
        '<!DOCTYPE html><html><head><meta charset="UTF-8">'
        f'<style>{css}</style></head><body>{html_body}</body></html>'
    )


def upload_html_template(html: str, name: str) -> dict:
    """Upload HTML to DocuSeal as a template. DocuSeal auto-detects signing fields."""
    return _docuseal_post('/templates/html', {
        'name': name,
        'documents': [{
            'name': name,
            'html': html,
            'size': 'A4',
        }],
    }, timeout=120)


def create_lease_submission(lease, signers: list, signing_mode: str = 'sequential') -> dict:
    """
    High-level function — two-step flow:
    1. Generate filled lease HTML with embedded signing field tags
    2. Upload to DocuSeal as an HTML template (auto-detects fields + positions)
    3. Create a submission from that template

    We use the two-step approach (template then submission) instead of the
    single-call POST /submissions/html because only templates expose field
    positions via GET /templates/{id}, which our custom signing UI needs
    to render field overlays on the PDF.

    signing_mode:
      - 'sequential' (default): signers go in order; DocuSeal's
        order='preserved' ensures each signer waits for the previous.
      - 'parallel': everyone signs at once.

    Returns {'template': {...}, 'submission': [...]}
    """
    tenant_name = lease.primary_tenant.full_name if lease.primary_tenant else 'Tenant'
    name = f"Lease - {tenant_name} - {lease.unit.property.name} Unit {lease.unit.unit_number}"

    # Step 1: Generate filled HTML with embedded DocuSeal signing field tags
    html = generate_lease_html(lease, num_signers=len(signers))

    # Step 2: Upload as HTML template — DocuSeal renders to PDF and
    # auto-detects field positions from the custom HTML tags
    template_data = upload_html_template(html, name)
    template_id = template_data['id']

    # Step 3: Create submission from the template
    # Role names must match the role attributes on the field tags in the HTML.
    docuseal_roles = _roles_from_template(template_data)

    submitters = []
    for idx, s in enumerate(signers):
        if docuseal_roles and idx < len(docuseal_roles):
            role = docuseal_roles[idx]
        else:
            role = 'First Party' if idx == 0 else f'Signer {idx + 1}'
        entry = {
            'name': s['name'],
            'email': s['email'],
            'role': role,
            # Never let DocuSeal send emails — Tremly sends its own emails
            # with links to the custom Vue signing page (/sign/<uuid>/).
            'send_email': False,
        }
        if signing_mode == 'sequential':
            entry['order'] = s.get('order', idx)
        submitters.append(entry)

    ds_order = 'preserved' if signing_mode == 'sequential' else 'random'
    submission_data = create_submission(template_id, submitters,
                                       send_email=False, order=ds_order)

    return {'template': template_data, 'submission': submission_data}


# ─── Native signing (no DocuSeal) ───────────────────────────────────────────

def create_native_submission(lease, signers: list, signing_mode: str = 'sequential') -> 'ESigningSubmission':
    """Create a native signing submission — no DocuSeal involved.

    Generates filled lease HTML, stores it as a snapshot, and creates
    signer records with locally-assigned IDs.
    """
    from apps.esigning.models import ESigningSubmission

    # Auto-inject landlord as last signer if not already present
    landlord_roles = {'landlord', 'lessor', 'owner'}
    has_landlord = any(s.get('role', '').lower() in landlord_roles for s in signers)
    if not has_landlord:
        ll_info = _get_landlord_info(lease)
        if ll_info and ll_info.get('email'):
            signers = list(signers) + [{
                'name': ll_info['name'], 'email': ll_info['email'],
                'phone': ll_info.get('phone', ''), 'role': 'Landlord',
                'send_email': True,
            }]

    html = generate_lease_html(lease, num_signers=len(signers), native=True)
    doc_hash = hashlib.sha256(html.encode()).hexdigest()

    # Map frontend signer roles to TipTap role names used in the HTML
    _role_to_tiptap = {
        'landlord': 'landlord', 'lessor': 'landlord',
        'tenant': 'tenant_1', 'tenant 1': 'tenant_1', 'co-tenant': 'tenant_2',
        'tenant 2': 'tenant_2', 'tenant 3': 'tenant_3',
        'witness': 'witness', 'agent': 'agent',
    }

    signer_records = []
    for idx, s in enumerate(signers):
        raw_role = s.get('role', f'Signer {idx + 1}')
        tiptap_role = _role_to_tiptap.get(raw_role.lower(), raw_role.lower().replace(' ', '_'))
        signer_records.append({
            'id': idx + 1,
            'name': s['name'],
            'email': s['email'],
            'phone': s.get('phone', ''),
            'role': tiptap_role,
            'status': 'pending',
            'order': s.get('order', idx),
            'completed_at': None,
            'signed_fields': [],
            'audit': None,
        })

    submission = ESigningSubmission.objects.create(
        lease=lease,
        signing_backend=ESigningSubmission.SigningBackend.NATIVE,
        status=ESigningSubmission.Status.PENDING,
        signing_mode=signing_mode,
        signers=signer_records,
        document_html=html,
        document_hash=doc_hash,
    )
    return submission


def extract_signer_fields(html: str, signer_role: str) -> list[dict]:
    """Extract signing field metadata from HTML for a specific signer role."""
    fields = []
    for m in re.finditer(r'<(signature|initials|date)-field\b([^>]*)>', html):
        tag_type = m.group(1)
        attrs = m.group(2)
        name_m = re.search(r'name="([^"]+)"', attrs)
        role_m = re.search(r'role="([^"]+)"', attrs)
        name = name_m.group(1) if name_m else ''
        role = role_m.group(1) if role_m else ''
        if role.lower() == signer_role.lower():
            fields.append({
                'fieldName': name,
                'fieldType': tag_type,
                'signerRole': role,
            })
    return fields


def get_already_signed_fields(submission) -> list[dict]:
    """Return fields that have already been signed by other signers."""
    signed = []
    for signer in submission.signers:
        if signer.get('status') == 'completed' and signer.get('signed_fields'):
            for field in signer['signed_fields']:
                signed.append({
                    'fieldName': field['fieldName'],
                    'fieldType': field['fieldType'],
                    'signerName': signer['name'],
                    'signedAt': field.get('signedAt', signer.get('completed_at', '')),
                })
    return signed


def _derive_merge_field_category(name: str) -> str:
    """Derive the category of a merge field from its name prefix."""
    n = name.lower()
    if n.startswith(('landlord', 'lessor')):
        return 'landlord'
    if n.startswith(('tenant', 'lessee', 'co_tenant', 'occupant')):
        return 'tenant'
    if n.startswith(('property', 'unit')) or n in ('city', 'province'):
        return 'property'
    if n.startswith(('lease', 'monthly', 'deposit', 'notice', 'water', 'electricity',
                      'max_', 'payment')):
        return 'lease'
    if n.startswith('agent'):
        return 'agent'
    return 'other'


def _role_to_category(signer_role: str) -> str:
    """Map a signer role string to a merge field category."""
    r = signer_role.lower()
    if 'landlord' in r or 'lessor' in r:
        return 'landlord'
    if 'tenant' in r or 'lessee' in r:
        return 'tenant'
    if 'agent' in r:
        return 'agent'
    return 'other'


def _field_belongs_to_role(field_name: str, signer_role: str) -> bool:
    """Check if a merge field belongs to a specific signer role."""
    f = field_name.lower()
    r = signer_role.lower()

    if 'landlord' in r or 'lessor' in r:
        return f.startswith('landlord') or f.startswith('lessor')
    if r in ('tenant_1', 'tenant', 'lessee'):
        # tenant_1 owns tenant_* (no number), tenant_1_*, and occupant_* fields
        return (
            (f.startswith('tenant_') and not re.match(r'^tenant_[2-9]', f))
            or f.startswith('occupant')
        )
    if r == 'tenant_2':
        return f.startswith('tenant_2_')
    if r == 'tenant_3':
        return f.startswith('tenant_3_')
    if 'agent' in r:
        return f.startswith('agent')
    return False


def extract_editable_merge_fields(html: str, signer_role: str) -> list[dict]:
    """Extract unfilled merge fields from HTML with editability based on signer role."""
    fields = []
    seen = set()
    for m in re.finditer(
        r'<span[^>]+data-type="merge-field"[^>]+data-field-name="([^"]+)"', html
    ):
        field_name = m.group(1)
        if field_name in seen:
            continue
        seen.add(field_name)
        category = _derive_merge_field_category(field_name)
        fields.append({
            'fieldName': field_name,
            'category': category,
            'editable': _field_belongs_to_role(field_name, signer_role),
            'label': field_name.replace('_', ' ').title(),
        })
    return fields


def apply_captured_data(html: str, captured_data: dict) -> str:
    """Replace merge field spans in HTML with filled values from captured data."""
    for field_name, value in captured_data.items():
        html = re.sub(
            rf'<span[^>]+data-field-name="{re.escape(field_name)}"[^>]*>.*?</span>',
            f'<span style="font-weight:600">{value}</span>',
            html, flags=re.DOTALL,
        )
    return html


def complete_native_signer(submission, signer_role: str, signed_fields: list, audit_data: dict,
                            captured_fields: dict | None = None):
    """Complete signing for a native signer.

    signed_fields: [{fieldName, fieldType, imageData}]
    audit_data: {ip_address, user_agent, consent_given_at}
    captured_fields: {fieldName: value} — merge field data entered by the signer

    Uses select_for_update for concurrency safety.
    """
    from apps.esigning.models import ESigningSubmission

    # Re-fetch with lock
    submission = ESigningSubmission.objects.select_for_update().get(pk=submission.pk)

    # Verify document integrity
    current_hash = hashlib.sha256(submission.document_html.encode()).hexdigest()
    if current_hash != submission.document_hash:
        raise ValueError('Document integrity check failed — document may have been tampered with.')

    # Find and update the signer
    now = timezone.now().isoformat()
    signer_found = False
    for signer in submission.signers:
        if signer.get('role', '').lower() == signer_role.lower():
            if signer.get('status') == 'completed':
                raise ValueError(f'Signer {signer_role} has already signed.')
            signer['status'] = 'completed'
            signer['completed_at'] = now
            signer['signed_fields'] = [
                {
                    'fieldName': f['fieldName'],
                    'fieldType': f['fieldType'],
                    'imageData': f['imageData'],
                    'signedAt': now,
                }
                for f in signed_fields
            ]
            signer['audit'] = {
                'ip_address': audit_data.get('ip_address', ''),
                'user_agent': audit_data.get('user_agent', ''),
                'consent_given_at': audit_data.get('consent_given_at', now),
                'consent_text': 'I agree to sign this document electronically and acknowledge that electronic signatures are legally binding.',
                'document_hash_at_signing': submission.document_hash,
                'fields_signed': [f['fieldName'] for f in signed_fields],
            }
            if captured_fields:
                signer['captured_fields'] = captured_fields
            signer_found = True
            break

    if not signer_found:
        raise ValueError(f'Signer with role {signer_role} not found.')

    # Store captured merge field data on the submission
    if captured_fields:
        submission.captured_data = {**(submission.captured_data or {}), **captured_fields}

    # Update submission status
    all_completed = all(s.get('status') == 'completed' for s in submission.signers)
    any_completed = any(s.get('status') == 'completed' for s in submission.signers)

    if all_completed:
        submission.status = ESigningSubmission.Status.COMPLETED
    elif any_completed:
        submission.status = ESigningSubmission.Status.IN_PROGRESS

    submission.save(update_fields=['signers', 'status', 'captured_data', 'updated_at'])

    return submission, all_completed


def sync_captured_data_to_models(submission):
    """Write captured merge field data back to Person/LeaseOccupant models.

    Called after signing to keep the /tenants page and Person records up to date.
    """
    from apps.accounts.models import Person
    from apps.leases.models import LeaseOccupant

    data = submission.captured_data or {}
    lease = getattr(submission, 'lease', None)
    if not lease or not data:
        return

    PERSON_FIELD_MAP = {
        'name': 'full_name',
        'id': 'id_number',
        'phone': 'phone',
        'email': 'email',
        'address': 'address',
        'employer': 'employer',
        'occupation': 'occupation',
        'emergency_contact': 'emergency_contact_name',
        'emergency_phone': 'emergency_contact_phone',
    }

    def _update_person(person, prefix):
        """Update a Person record with captured data matching the prefix."""
        updated_fields = []
        for suffix, model_field in PERSON_FIELD_MAP.items():
            val = data.get(f'{prefix}_{suffix}', '').strip()
            if val and val != '—':
                setattr(person, model_field, val)
                updated_fields.append(model_field)
        # Handle date_of_birth separately
        dob_val = data.get(f'{prefix}_dob', '').strip()
        if dob_val and dob_val != '—':
            try:
                from datetime import date as dt_date
                person.date_of_birth = dt_date.fromisoformat(dob_val)
                updated_fields.append('date_of_birth')
            except (ValueError, TypeError):
                pass
        if updated_fields:
            person.save(update_fields=updated_fields)

    # Primary tenant
    if lease.primary_tenant:
        _update_person(lease.primary_tenant, 'tenant')
        _update_person(lease.primary_tenant, 'tenant_1')

    # Co-tenants
    for i, ct in enumerate(lease.co_tenants.select_related('person').all()[:3], start=2):
        _update_person(ct.person, f'tenant_{i}')

    # Occupants (create Person + LeaseOccupant if new)
    for i in range(1, 5):
        occ_name = data.get(f'occupant_{i}_name', '').strip()
        if occ_name and occ_name != '—':
            person, created = Person.objects.get_or_create(
                full_name=occ_name,
                defaults={
                    'id_number': data.get(f'occupant_{i}_id', '').strip(),
                }
            )
            if not created:
                _update_person(person, f'occupant_{i}')
            LeaseOccupant.objects.get_or_create(
                lease=lease, person=person,
                defaults={
                    'relationship_to_tenant': data.get(f'occupant_{i}_relationship', '').strip(),
                }
            )


def _clean_tiptap_html_for_print(html: str) -> str:
    """Strip TipTap editor-only markup and normalise HTML for Chromium print rendering.

    Handles PaginationPlus wrappers, editor classes, empty spacer paragraphs,
    data-page-break divs, and other editor artifacts that should not appear in
    the final PDF output.
    """
    # ── PaginationPlus page-break wrapper divs → clean CSS page breaks ──
    html = re.sub(
        r'<div[^>]*page-break-after:\s*always[^>]*>(.*?)</div>',
        r'\1<div style="page-break-after:always;"></div>',
        html, flags=re.DOTALL,
    )

    # ── data-page-break divs (from PageBreakNode) → CSS page breaks ──
    html = re.sub(
        r'<div[^>]*data-page-break[^>]*>.*?</div>',
        '<div style="page-break-after:always;"></div>',
        html, flags=re.DOTALL,
    )

    # ── Remove PaginationPlus runtime classes from the root editor element ──
    html = re.sub(r'\s*class="[^"]*rm-with-pagination[^"]*"', '', html)
    html = re.sub(r'\s*class="[^"]*tiptap-paged[^"]*"', '', html)
    html = re.sub(r'\s*class="[^"]*ProseMirror[^"]*"', '', html)

    # ── Remove PaginationPlus gap/footer/header overlay divs ──
    html = re.sub(r'<div[^>]*class="[^"]*rm-pagination-gap[^"]*"[^>]*>.*?</div>', '', html, flags=re.DOTALL)
    html = re.sub(r'<div[^>]*class="[^"]*rm-page-footer[^"]*"[^>]*>.*?</div>', '', html, flags=re.DOTALL)
    html = re.sub(r'<div[^>]*class="[^"]*rm-page-header[^"]*"[^>]*>.*?</div>', '', html, flags=re.DOTALL)
    html = re.sub(r'<div[^>]*class="[^"]*page-overlays-container[^"]*"[^>]*>.*?</div>', '', html, flags=re.DOTALL)
    html = re.sub(r'<div[^>]*class="[^"]*page-sim-gap[^"]*"[^>]*>.*?</div>', '', html, flags=re.DOTALL)

    # ── Remove contenteditable and data-drag-handle attributes ──
    html = re.sub(r'\s*contenteditable="[^"]*"', '', html)
    html = re.sub(r'\s*data-drag-handle(?:="[^"]*")?', '', html)
    html = re.sub(r'\s*draggable="[^"]*"', '', html)

    # ── Remove inline min-height/padding that PageSimulation adds to editor div ──
    html = re.sub(r'style="[^"]*min-height:\s*\d+px[^"]*"', '', html)

    # ── Remove empty data attributes left over from node views ──
    html = re.sub(r'\s*data-node-view-wrapper(?:="[^"]*")?', '', html)
    html = re.sub(r'\s*data-node-view-content(?:="[^"]*")?', '', html)

    # ── Remove inline initials rows ──────────────────────────────────────
    # TipTap PaginationPlus places initials in right-aligned <p> tags before
    # page breaks, preceded by empty <p></p> spacers. These don't translate
    # to print — initials are rendered in the Gotenberg footer instead.
    # Remove: right-aligned <p> containing only signing field tags or initials imgs
    html = re.sub(
        r'<p[^>]*style="[^"]*text-align:\s*right[^"]*"[^>]*>'
        r'(?:\s*(?:<span>)?\s*(?:<(?:initials-field|signature-field|date-field)\b[^>]*>[^<]*'
        r'</(?:initials-field|signature-field|date-field)>'
        r'|<img[^>]*height:\s*16px[^>]*/?>\s*)'
        r'(?:</span>\s*)?)+\s*</p>',
        '',
        html, flags=re.DOTALL,
    )

    # ── Remove forced page breaks (let Chromium paginate naturally) ──────
    html = re.sub(
        r'<div[^>]*style="[^"]*page-break-after:\s*always[^"]*"[^>]*>\s*</div>',
        '',
        html,
    )

    # ── Collapse runs of empty paragraphs used as TipTap spacers (keep max 1) ──
    html = re.sub(r'(<p>\s*</p>\s*){2,}', '<p></p>', html)

    return html


# ── Professional print CSS for signed lease PDFs ────────────────────────
# Gotenberg uses Chromium, so we have full modern CSS support.
_SIGNED_PDF_CSS = """
@page {
    size: A4;
    margin: 20mm 18mm 22mm 18mm;
}

/* ── Base typography — professional legal document ── */
body {
    font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
    font-size: 10.5pt;
    line-height: 1.6;
    color: #1a1a1a;
    margin: 0;
    padding: 0;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
}

/* ── Headings ── */
h1 {
    font-size: 15pt;
    font-weight: 700;
    text-align: center;
    margin: 0 0 6pt;
    color: #111;
    letter-spacing: -0.01em;
}

h2 {
    font-size: 11.5pt;
    font-weight: 700;
    margin: 14pt 0 4pt;
    color: #1a1a1a;
    border-bottom: 0.5pt solid #d0d0d0;
    padding-bottom: 2pt;
}

h3 {
    font-size: 10.5pt;
    font-weight: 700;
    margin: 10pt 0 3pt;
    color: #1a1a1a;
}

/* ── Paragraphs and lists ── */
p {
    margin: 3pt 0;
    orphans: 3;
    widows: 3;
}

li {
    margin: 2pt 0;
}

ul, ol {
    padding-left: 20pt;
    margin: 4pt 0;
}

/* ── Tables ── */
table {
    border-collapse: collapse;
    width: 100%;
    margin: 6pt 0;
    page-break-inside: auto;
}

thead {
    display: table-header-group;
}

tr {
    page-break-inside: avoid;
}

td, th {
    border: 0.5pt solid #c0c0c0;
    padding: 5pt 7pt;
    font-size: 10pt;
    vertical-align: top;
}

th {
    background-color: #f5f5f5;
    font-weight: 600;
    text-align: left;
}

/* ── Signatures ── */
img[src^="data:image"] {
    max-width: 220px;
    max-height: 80px;
}

/* ── Filled merge field values ── */
.pdf-field-value {
    font-weight: 600;
    color: #111;
}

/* ── Unfilled field placeholder ── */
.pdf-field-blank {
    display: inline-block;
    min-width: 80px;
    border-bottom: 0.5pt solid #999;
    height: 1em;
    vertical-align: baseline;
}

/* ── Unsigned signature placeholder ── */
.pdf-sig-blank {
    display: inline-block;
    width: 180px;
    border-bottom: 0.5pt solid #999;
    height: 1.2em;
    vertical-align: middle;
}

.pdf-initials-blank {
    display: inline-block;
    width: 50px;
    border-bottom: 0.5pt solid #bbb;
    height: 1em;
    vertical-align: baseline;
}

.pdf-date-blank {
    color: #999;
    letter-spacing: 0.5pt;
}

/* ── Horizontal rule styling ── */
hr {
    border: none;
    border-top: 0.5pt solid #d0d0d0;
    margin: 8pt 0;
}

/* ── Audit trail page ── */
.audit-trail {
    page-break-before: always;
    padding-top: 8pt;
}

.audit-trail h2 {
    font-size: 13pt;
    font-weight: 700;
    color: #1a1a1a;
    margin: 0 0 4pt;
    padding-bottom: 4pt;
    border-bottom: 1.5pt solid #2B2D6E;
}

.audit-trail .audit-meta {
    font-size: 8pt;
    color: #666;
    margin: 2pt 0 10pt;
    font-family: 'Courier New', monospace;
    word-break: break-all;
}

.audit-trail table {
    font-size: 8.5pt;
    margin-top: 6pt;
}

.audit-trail td, .audit-trail th {
    padding: 4pt 6pt;
    font-size: 8.5pt;
    border: 0.5pt solid #d0d0d0;
}

.audit-trail th {
    background: #f0f0f4;
    color: #2B2D6E;
    font-weight: 600;
    font-size: 8pt;
    text-transform: uppercase;
    letter-spacing: 0.3pt;
}

.audit-trail .audit-ua {
    font-size: 7pt;
    color: #888;
    word-break: break-all;
    max-width: 120pt;
}

.audit-trail .audit-footer {
    margin-top: 16pt;
    padding-top: 8pt;
    border-top: 0.5pt solid #e0e0e0;
    font-size: 7.5pt;
    color: #888;
    line-height: 1.5;
}

.audit-trail .audit-footer strong {
    color: #555;
}
"""


def generate_signed_pdf(submission) -> bytes:
    """Generate a PDF with embedded signature images from a completed native submission.

    Uses Gotenberg (Chromium) for pixel-perfect rendering that matches the TipTap editor.
    Falls back to xhtml2pdf if Gotenberg is unavailable.
    """
    from .gotenberg import html_to_pdf as gotenberg_html_to_pdf

    html = submission.document_html

    # ── 1. Clean TipTap editor artifacts for print ──────────────────────
    html = _clean_tiptap_html_for_print(html)

    # ── 2. Replace unfilled merge fields with captured data ─────────────
    html = apply_captured_data(html, submission.captured_data or {})

    # ── 3. Replace signing field tags with signature images or date text ─
    for signer in submission.signers:
        for field in signer.get('signed_fields', []):
            field_name = field['fieldName']
            field_type = field['fieldType']
            image_data = field.get('imageData', '')

            if field_type in ('signature', 'initials'):
                if field_type == 'initials':
                    replacement = (
                        f'<img src="{image_data}" '
                        f'style="height:16px;display:inline;vertical-align:baseline;" />'
                    )
                else:
                    replacement = (
                        f'<img src="{image_data}" '
                        f'style="height:55px;display:inline-block;vertical-align:middle;" />'
                    )
            elif field_type == 'date':
                signed_date = field.get("signedAt", "")[:10]
                replacement = f'<span class="pdf-field-value">{signed_date}</span>'
            else:
                continue

            # Replace the field tag by name
            html = re.sub(
                rf'<{field_type}-field\b[^>]*name="{re.escape(field_name)}"[^>]*>[^<]*</{field_type}-field>',
                replacement, html,
            )

    # ── 4. Clean up remaining unsigned field tags → styled placeholders ─
    html = re.sub(
        r'<signature-field\b[^>]*>[^<]*</signature-field>',
        '<span class="pdf-sig-blank">&nbsp;</span>',
        html,
    )
    html = re.sub(
        r'<initials-field\b[^>]*>[^<]*</initials-field>',
        '<span class="pdf-initials-blank">&nbsp;</span>',
        html,
    )
    html = re.sub(
        r'<date-field\b[^>]*>[^<]*</date-field>',
        '<span class="pdf-date-blank">____/____/________</span>',
        html,
    )

    # ── 5. Clean up remaining unfilled merge-field spans ────────────────
    def _clean_merge_span(m: re.Match) -> str:
        inner = m.group(1)
        if inner.strip().startswith('{{'):
            return '<span class="pdf-field-blank">&nbsp;</span>'
        return f'<span class="pdf-field-value">{inner}</span>'

    html = re.sub(
        r'<span[^>]*data-type="merge-field"[^>]*>(.*?)</span>',
        _clean_merge_span, html, flags=re.DOTALL,
    )

    # ── 6. Build audit trail page ───────────────────────────────────────
    audit_rows = ''
    for signer in submission.signers:
        audit = signer.get('audit', {}) or {}
        completed = signer.get('completed_at', '')
        # Format ISO timestamp to human-readable
        if completed and len(completed) >= 16:
            completed = completed[:10] + ' ' + completed[11:16]
        audit_rows += (
            f'<tr>'
            f'<td>{signer.get("name", "")}</td>'
            f'<td>{signer.get("email", "")}</td>'
            f'<td>{signer.get("role", "").replace("_", " ").title()}</td>'
            f'<td>{audit.get("ip_address", "")}</td>'
            f'<td>{completed}</td>'
            f'<td class="audit-ua">{audit.get("user_agent", "")[:100]}</td>'
            f'</tr>'
        )

    audit_page = f'''
    <div class="audit-trail">
        <h2>Audit Trail</h2>
        <p class="audit-meta">Document Hash (SHA-256): {submission.document_hash}</p>
        <table>
            <thead>
                <tr>
                    <th>Signer</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>IP Address</th>
                    <th>Signed At</th>
                    <th>User Agent</th>
                </tr>
            </thead>
            <tbody>{audit_rows}</tbody>
        </table>
        <div class="audit-footer">
            <p>This document was signed electronically via <strong>Klikk Property Management</strong>.</p>
            <p>All parties consented to electronic signatures as legally binding under the
            Electronic Communications and Transactions Act 25 of 2002 (ECTA).</p>
        </div>
    </div>
    '''

    # ── 7. Inject print CSS and audit trail into the HTML document ──────
    # Replace the existing <style> block with our professional print CSS
    html = re.sub(
        r'<style[^>]*>.*?</style>',
        f'<style>{_SIGNED_PDF_CSS}</style>',
        html, count=1, flags=re.DOTALL,
    )

    # Insert audit page before </body>
    html = html.replace('</body>', f'{audit_page}</body>')

    # ── 8. Build footer with initials for every page ─────────────────────
    # Collect one initials image per signer (first initials field found).
    initials_imgs = {}  # role → base64 data URI
    for signer in submission.signers:
        role = signer.get('role', '')
        for field in signer.get('signed_fields', []):
            if field['fieldType'] == 'initials' and field.get('imageData'):
                if role not in initials_imgs:
                    initials_imgs[role] = field['imageData']
                break

    if initials_imgs:
        initials_html_parts = []
        for _role, img_data in initials_imgs.items():
            initials_html_parts.append(
                f'<img src="{img_data}" />'
            )
        footer_html = (
            '<!DOCTYPE html><html><head><style>'
            'body { font-size: 8pt; font-family: Arial, sans-serif; margin: 0; '
            'padding: 0; -webkit-print-color-adjust: exact; }'
            'table { width: 100%; border-collapse: collapse; }'
            'td { padding: 0; vertical-align: middle; }'
            '.left { color: #999; font-size: 7pt; }'
            '.right { text-align: right; white-space: nowrap; }'
            '.right img { height: 14px; margin-left: 6px; vertical-align: middle; }'
            '</style></head><body>'
            '<table><tr>'
            '<td class="left">Page <span class="pageNumber"></span>'
            ' of <span class="totalPages"></span></td>'
            f'<td class="right">{"".join(initials_html_parts)}</td>'
            '</tr></table></body></html>'
        )
    else:
        # No signed initials — simple page number footer
        footer_html = (
            '<!DOCTYPE html><html><head><style>'
            'body { font-size: 8pt; font-family: Arial, sans-serif; margin: 0 2cm; '
            'color: #999; }'
            '</style></head><body>'
            'Page <span class="pageNumber"></span>'
            ' of <span class="totalPages"></span>'
            '</body></html>'
        )

    # ── 9. Render to PDF via Gotenberg (Chromium) ───────────────────────
    try:
        return gotenberg_html_to_pdf(html, footer_html=footer_html,
                                     margin_bottom=0.79)
    except Exception as exc:
        logger.warning('Gotenberg PDF generation failed, falling back to xhtml2pdf: %s', exc)

    # Fallback: xhtml2pdf (legacy — less accurate CSS rendering)
    from io import BytesIO
    from xhtml2pdf import pisa

    buffer = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=buffer)
    if pisa_status.err:
        logger.error('PDF generation failed with %d errors', pisa_status.err)
        raise ValueError(f'PDF generation failed with {pisa_status.err} errors')

    return buffer.getvalue()
