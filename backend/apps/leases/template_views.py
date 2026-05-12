import io
import json
import logging
import os
import re
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import IsAgentOrAdmin
from apps.accounts.models import User
from apps.accounts.scoping import (
    AgencyScopedQuerysetMixin,
    AgencyStampedCreateMixin,
    _is_admin,
)
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework import status, generics

logger = logging.getLogger(__name__)


def _extract_html(content_html: str) -> str:
    """Extract HTML from content_html field — handles JSON (v1) and legacy HTML."""
    raw = (content_html or "").strip()
    if not raw:
        return ""
    if raw.startswith("{"):
        try:
            doc = json.loads(raw)
            if isinstance(doc, dict) and doc.get("v") in (1, 2) and isinstance(doc.get("html"), str):
                return doc["html"]
        except (json.JSONDecodeError, TypeError):
            pass
    return raw


def _get_anthropic_api_key() -> str:
    """
    Return the Anthropic API key.
    Falls back to reading .env directly because Claude Code clears os.environ,
    causing django-decouple to return the default empty string.
    """
    from django.conf import settings
    key = getattr(settings, "ANTHROPIC_API_KEY", "") or ""
    if key:
        return key
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    try:
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("ANTHROPIC_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return ""

from .models import LeaseTemplate
from .serializers import LeaseTemplateSerializer

# Lazy import so startup doesn't fail if docxtpl isn't installed yet
try:
    from docxtpl import DocxTemplate
except ImportError:
    DocxTemplate = None


_PDF_TO_TEMPLATE_SYSTEM = (
    "You are an expert at converting South African lease agreement PDFs into reusable HTML templates. "
    "Read the PDF and reproduce its full content as clean HTML, replacing all tenant-specific, "
    "property-specific, and financial values with merge fields. "
    "Output the HTML first, then a line containing exactly '---FIELDS---', "
    "then a JSON array of all merge field names used. No markdown fences, no other commentary."
)

_PDF_TO_TEMPLATE_PROMPT = """Convert this lease PDF into a reusable HTML template.

OUTPUT FORMAT (follow exactly):
<full HTML content here>
---FIELDS---
["field_name_1", "field_name_2", ...]

RULES:
1. Reproduce the complete document structure (headings, numbered clauses, tables, annexures).
2. Do NOT include <html>, <head>, <body>, or <style> wrapper tags. Start directly with content tags.
3. Replace every specific value with a merge field using this HTML pattern:
   <span data-merge-field="field_name">{{field_name}}</span>
4. Use these standard field names (add others as needed):
   - landlord_name, landlord_reg_number, landlord_address, landlord_email
   - agent_name, agent_reg_number, agent_address, agent_email
   - infraco_name, infraco_reg_number, infraco_address, infraco_email
   - tenant_name, tenant_id_number, tenant_address, tenant_email, tenant_phone
   - co_tenant_name, co_tenant_id_number, co_tenant_address, co_tenant_email, co_tenant_phone
   - guarantor_name, guarantor_id_number, guarantor_address, guarantor_email, guarantor_phone
   - property_address, property_suburb, property_city, property_province, property_postal_code
   - unit_number, unit_type, building_name
   - lease_start_date, lease_end_date, key_return_date
   - monthly_rent, deposit_amount, deposit_multiplier, payment_frequency
   - escalation_percent, late_payment_interest_rate, notice_period_days
   - annual_discount_percent, half_yearly_discount_percent
   - parking_fee, parking_bays
   - bank_name, bank_branch, bank_account_number, bank_reference
   - infraco_bank_name, infraco_bank_branch, infraco_bank_account, infraco_bank_reference
   - landlord_signature_1, tenant_signature_1, co_tenant_signature_1
   - landlord_initials_1, tenant_initials_1, co_tenant_initials_1
5. For signature/initials blocks use:
   <div data-type="signature-block" data-field-type="signature" data-signer-role="landlord" data-field-name="landlord_signature_1" style="width:200px;height:60px;display:inline-block;border-bottom:1px solid #000;margin:8px 0;">{{landlord_signature_1}}</div>
6. Preserve all clause numbering, headings, and table structures using <h1>-<h4>, <table>, <tr>, <td>.
7. Keep all static boilerplate text exactly as written (definitions, legal clauses, etc.).
8. Replace all filled-in tenant-specific handwritten or typed values with merge fields.
9. After the HTML, output exactly one line: ---FIELDS---
10. On the next line, output a JSON array of all merge field names used (deduplicated, no extras).

The lease is attached as a PDF. Read all pages including all tables and annexures."""

_FIELDS_SEPARATOR = "---FIELDS---"


def _pdf_to_template_html(pdf_bytes: bytes, api_key: str):
    """Convert a PDF lease to TipTap-compatible HTML with merge fields via Claude.

    Returns (html: str, fields: list[str]) on success, raises RuntimeError on failure.
    Uses a text separator format to avoid JSON-encoding a large HTML string.
    """
    import anthropic
    import base64

    client = anthropic.Anthropic(api_key=api_key)
    b64_pdf = base64.standard_b64encode(pdf_bytes).decode("ascii")
    # Use streaming — required by SDK for max_tokens > threshold (~10 min limit)
    raw_parts = []
    with client.messages.stream(
        model="claude-sonnet-4-20250514",
        max_tokens=32000,
        system=_PDF_TO_TEMPLATE_SYSTEM,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": b64_pdf,
                    },
                },
                {"type": "text", "text": _PDF_TO_TEMPLATE_PROMPT},
            ],
        }],
    ) as stream:
        for text in stream.text_stream:
            raw_parts.append(text)
    raw = "".join(raw_parts).strip()

    # Split on the separator line
    if _FIELDS_SEPARATOR in raw:
        html_part, fields_part = raw.split(_FIELDS_SEPARATOR, 1)
        html = html_part.strip()
        fields_part = fields_part.strip()
        # Strip any accidental markdown fences around the fields JSON
        fields_part = re.sub(r"^```[a-z]*\n?", "", fields_part)
        fields_part = re.sub(r"\n?```$", "", fields_part.strip())
        try:
            fields = json.loads(fields_part)
            if not isinstance(fields, list):
                fields = []
        except json.JSONDecodeError:
            # Fall back to regex extraction of field names from HTML
            fields = list(dict.fromkeys(re.findall(r'data-merge-field="([^"]+)"', html)))
    else:
        # No separator — treat entire response as HTML and extract fields from it
        html = re.sub(r"^```[a-z]*\n?", "", raw)
        html = re.sub(r"\n?```$", "", html.strip())
        fields = list(dict.fromkeys(re.findall(r'data-merge-field="([^"]+)"', html)))

    if not html:
        raise RuntimeError("Claude returned empty HTML.")
    return html, fields


def _scoped_lease_templates(request):
    """
    Return the LeaseTemplate queryset scoped to the caller's agency.

    Admins (or anonymous flows that should never reach these views) get the
    full queryset; everyone else is filtered to their own agency_id, with
    users lacking an agency seeing nothing.
    """
    user = getattr(request, "user", None)
    if _is_admin(user):
        return LeaseTemplate.objects.all()
    agency_id = getattr(user, "agency_id", None) if user else None
    if agency_id is None:
        return LeaseTemplate.objects.none()
    return LeaseTemplate.objects.filter(agency_id=agency_id)


def _resolve_agency_id_for_create(request):
    """
    Resolve the agency_id to stamp on a LeaseTemplate (or related per-tenant
    object) created via a non-DRF-default code path (e.g. raw Model.objects.create).

    Mirrors AgencyStampedCreateMixin: admins may pass `agency` in the payload;
    non-admins are forced to their own agency. Returns the agency_id or None
    if the caller is allowed to create unscoped (admin without explicit agency
    is treated as an error to keep behaviour consistent).
    """
    user = getattr(request, "user", None)
    if _is_admin(user):
        agency_id = request.data.get("agency") or getattr(user, "agency_id", None)
        return agency_id  # may be None — caller decides what to do
    return getattr(user, "agency_id", None)


class LeaseTemplateListView(
    AgencyScopedQuerysetMixin, generics.ListCreateAPIView
):
    """
    GET  /api/v1/leases/templates/ — list active lease templates.
    POST /api/v1/leases/templates/ — upload a new DOCX template (multipart).

    Multipart POST fields:
      name        (string, required)
      docx_file   (file, required — .docx)
      version     (string, optional, default "1.0")
      province    (string, optional)
    """
    serializer_class = LeaseTemplateSerializer
    permission_classes = [IsAgentOrAdmin]
    parser_classes = [*generics.ListCreateAPIView.parser_classes]
    queryset = LeaseTemplate.objects.all()

    def get_queryset(self):
        # AgencyScopedQuerysetMixin filters to the caller's agency_id; layer
        # the existing is_active filter on top.
        return super().get_queryset().filter(is_active=True)

    def create(self, request, *args, **kwargs):
        name = (request.data.get("name") or "").strip()
        if not name:
            return Response({"error": "name is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Phase 2.4 — stamp the caller's agency on every LeaseTemplate created
        # in this method. We call Model.objects.create directly here (not via
        # DRF perform_create), so the AgencyStampedCreateMixin doesn't apply.
        agency_id = _resolve_agency_id_for_create(request)
        user = getattr(request, "user", None)
        if agency_id is None and not _is_admin(user):
            return Response(
                {"detail": "Your user account is not linked to an agency. Contact your administrator."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Duplicate from existing template ──────────────────────────────
        duplicate_from = request.data.get("duplicate_from")
        if duplicate_from:
            try:
                source = _scoped_lease_templates(request).get(pk=int(duplicate_from))
            except (LeaseTemplate.DoesNotExist, ValueError, TypeError):
                return Response({"error": "Source template not found."}, status=status.HTTP_404_NOT_FOUND)

            tmpl = LeaseTemplate.objects.create(
                agency_id=agency_id,
                name=name,
                version=request.data.get("version") or "1.0",
                province=request.data.get("province") or source.province or "",
                content_html=source.content_html,
                header_html=source.header_html,
                footer_html=source.footer_html,
                fields_schema=source.fields_schema or [],
            )
            serializer = LeaseTemplateSerializer(tmpl, context={"request": request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        # ── Blank template (no file) ──────────────────────────────────────
        uploaded_file = request.FILES.get("docx_file") or request.FILES.get("template_file")
        if not uploaded_file:
            tmpl = LeaseTemplate.objects.create(
                agency_id=agency_id,
                name=name,
                version=request.data.get("version") or "1.0",
                province=request.data.get("province") or "",
                content_html=request.data.get("content_html") or "",
                header_html=request.data.get("header_html") or "",
                footer_html=request.data.get("footer_html") or "",
            )
            serializer = LeaseTemplateSerializer(tmpl, context={"request": request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        # ── File upload (DOCX / PDF) ──────────────────────────────────────
        lower_name = uploaded_file.name.lower()
        is_docx = lower_name.endswith(".docx")
        is_pdf = lower_name.endswith(".pdf")
        if not is_docx and not is_pdf:
            return Response({"error": "Only .docx or .pdf files are accepted."}, status=status.HTTP_400_BAD_REQUEST)

        # Read PDF bytes before the ORM save (Django may advance the file pointer during storage write)
        pdf_bytes = uploaded_file.read() if is_pdf else None

        tmpl = LeaseTemplate.objects.create(
            agency_id=agency_id,
            name=name,
            version=request.data.get("version") or "1.0",
            province=request.data.get("province") or "",
            docx_file=uploaded_file,
        )

        # Discover merge fields for DOCX; convert PDF content to template HTML via Claude
        if is_docx and DocxTemplate is not None:
            try:
                doc = DocxTemplate(tmpl.docx_file.path)
                variables = list(doc.get_undeclared_template_variables())
                tmpl.fields_schema = variables
                tmpl.save(update_fields=["fields_schema"])
            except Exception:
                pass  # field discovery is best-effort

        elif is_pdf and pdf_bytes:
            import logging
            import threading
            _log = logging.getLogger(__name__)
            api_key = _get_anthropic_api_key()
            if not api_key:
                _log.warning("PDF template conversion skipped: ANTHROPIC_API_KEY not set")
            else:
                tmpl_id = tmpl.id

                def _convert_in_background():
                    """Run Claude PDF→HTML conversion in a daemon thread so the HTTP response returns immediately."""
                    try:
                        html, fields = _pdf_to_template_html(pdf_bytes, api_key)
                        from .models import LeaseTemplate as _LT
                        _LT.objects.filter(pk=tmpl_id).update(
                            content_html=json.dumps({
                                "v": 1,
                                "html": html,
                                "fields": [{"name": f, "type": "text"} for f in fields],
                            }),
                            fields_schema=fields,
                        )
                        _log.info("PDF template %s converted: %d chars, %d fields", tmpl_id, len(html), len(fields))
                    except Exception as exc:
                        _log.warning("PDF template %s conversion failed: %s", tmpl_id, exc, exc_info=True)

                t = threading.Thread(target=_convert_in_background, daemon=True)
                t.start()

        serializer = LeaseTemplateSerializer(tmpl, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LeaseTemplateDetailView(
    AgencyScopedQuerysetMixin, generics.RetrieveUpdateDestroyAPIView
):
    """
    GET    /api/v1/leases/templates/{id}/ — retrieve
    PATCH  /api/v1/leases/templates/{id}/ — update (supports multipart docx_file upload)
    DELETE /api/v1/leases/templates/{id}/ — delete
    """
    serializer_class = LeaseTemplateSerializer
    permission_classes = [IsAgentOrAdmin]
    queryset = LeaseTemplate.objects.all()

    def perform_update(self, serializer):
        instance = serializer.save()
        # Re-discover merge fields when a new DOCX file is uploaded
        if "docx_file" in self.request.FILES and instance.docx_file:
            lower = instance.docx_file.name.lower()
            if lower.endswith(".docx") and DocxTemplate is not None:
                try:
                    doc = DocxTemplate(instance.docx_file.path)
                    variables = list(doc.get_undeclared_template_variables())
                    instance.fields_schema = variables
                    instance.save(update_fields=["fields_schema"])
                except Exception:
                    pass  # field discovery is best-effort

        # Run RHA compliance check on save (but do NOT auto-renumber —
        # renumbering overrides intentional user edits and triggers a full
        # editor reload that can lose block field placements).
        # Renumbering is available on-demand via the AI chat "renumber_sections" tool.
        html = _extract_html(instance.content_html)
        if html:
            self._compliance_report = _check_rha_compliance(html)

    def update(self, request, *args, **kwargs):
        self._compliance_report = None
        response = super().update(request, *args, **kwargs)
        if response.status_code == 200:
            if self._compliance_report:
                response.data["compliance"] = self._compliance_report
        return response


class GenerateLeaseDocumentView(APIView):
    """
    POST /api/v1/leases/generate/

    Fill a DOCX lease template with provided context values and return
    the rendered document as a file download.

    Request body:
    {
        "template_id": 1,      # optional — uses first active template if omitted
        "context": {
            "landlord_name": "...",
            "tenant_name": "...",
            "monthly_rent": "R 12 500",
            ...
        }
    }
    """
    permission_classes = [IsAgentOrAdmin]

    def post(self, request):
        if DocxTemplate is None:
            return Response(
                {"error": "docxtpl is not installed. Run: pip install docxtpl"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        template_id = request.data.get("template_id")
        context = request.data.get("context") or {}

        scoped_qs = _scoped_lease_templates(request)
        if template_id:
            try:
                tmpl = scoped_qs.get(pk=template_id, is_active=True)
            except LeaseTemplate.DoesNotExist:
                return Response({"error": "Template not found."}, status=status.HTTP_404_NOT_FOUND)
        else:
            tmpl = scoped_qs.filter(is_active=True).first()
            if not tmpl:
                return Response(
                    {"error": "No active lease template found. Upload one first."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        if not tmpl.docx_file or not os.path.exists(tmpl.docx_file.path):
            return Response({"error": "Template file not found on disk."}, status=status.HTTP_404_NOT_FOUND)

        # Render the template
        doc = DocxTemplate(tmpl.docx_file.path)
        doc.render(_sanitize_context(context))

        # Stream as DOCX download
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        filename = f"lease_{context.get('tenant_name', 'draft').replace(' ', '_')}.docx"
        response = HttpResponse(
            buffer.read(),
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class LeaseTemplatePreviewView(APIView):
    """
    GET /api/v1/leases/templates/{id}/preview/
    Returns template paragraphs + fields for the template editor middle panel.
    """
    permission_classes = [IsAgentOrAdmin]

    def get(self, request, pk):
        try:
            tmpl = _scoped_lease_templates(request).get(pk=pk)
        except LeaseTemplate.DoesNotExist:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if not tmpl.docx_file:
            return Response({"error": "No file attached."}, status=status.HTTP_404_NOT_FOUND)

        try:
            file_path = tmpl.docx_file.path
        except Exception:
            return Response({"error": "File not found on disk."}, status=status.HTTP_404_NOT_FOUND)

        lower = file_path.lower()
        if lower.endswith(".pdf"):
            pdf_url = request.build_absolute_uri(tmpl.docx_file.url) if tmpl.docx_file else None
            return Response({
                "type": "pdf",
                "name": tmpl.name,
                "fields": tmpl.fields_schema,
                "paragraphs": [],
                "pdf_url": pdf_url,
            })

        try:
            from docx import Document as DocxDocument
        except ImportError:
            return Response({"error": "python-docx not installed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if not os.path.exists(file_path):
            return Response({"error": "File not found on disk."}, status=status.HTTP_404_NOT_FOUND)

        doc = DocxDocument(file_path)
        paragraphs = []
        for p in doc.paragraphs:
            text = p.text
            if not text.strip():
                continue
            para = {"style": p.style.name, "text": text}
            # Extract dominant run-level formatting from the first styled run
            for run in p.runs:
                if not run.text.strip():
                    continue
                if run.font.size:
                    para["font_size_pt"] = round(run.font.size.pt, 1)
                if run.font.name:
                    para["font_family"] = run.font.name
                if run.bold:
                    para["bold"] = True
                if run.italic:
                    para["italic"] = True
                if run.font.color and run.font.color.type is not None:
                    try:
                        rgb = run.font.color.rgb
                        para["color"] = f"#{rgb}"
                    except Exception:
                        pass
                break  # only sample first styled run
            # Paragraph-level alignment
            if p.alignment is not None:
                from docx.enum.text import WD_ALIGN_PARAGRAPH
                _align_map = {
                    WD_ALIGN_PARAGRAPH.CENTER: "center",
                    WD_ALIGN_PARAGRAPH.RIGHT: "right",
                    WD_ALIGN_PARAGRAPH.JUSTIFY: "justify",
                }
                al = _align_map.get(p.alignment)
                if al:
                    para["text_align"] = al
            paragraphs.append(para)

        return Response({
            "type": "docx",
            "name": tmpl.name,
            "fields": tmpl.fields_schema,
            "paragraphs": paragraphs,
            "content_html": _extract_html(tmpl.content_html),
            "header_html": tmpl.header_html or "",
            "footer_html": tmpl.footer_html or "",
        })


import json as _json

def _detect_fields_from_html(html: str) -> list:
    # Span-wrapped fields: <span data-merge-field="field_name">
    span_fields = re.findall(r'data-merge-field="([^"]+)"', html)
    # Brace-style fields written by the AI or typed: {{ field_name }}
    brace_fields = re.findall(r'\{\{\s*([\w]+)\s*\}\}', html)
    return list(dict.fromkeys(span_fields + brace_fields))


# ── Compact JSON ↔ HTML conversion (RAG-friendly representation) ──────────

_MERGE_SPAN_RE = re.compile(r'<span[^>]+data-merge-field="([^"]+)"[^>]*>.*?</span>', re.DOTALL)
_TAG_RE        = re.compile(r'<[^>]+>')

def _strip_tags(s: str) -> str:
    """Remove HTML tags, collapse whitespace."""
    s = _MERGE_SPAN_RE.sub(r'{{ \1 }}', s)  # preserve merge fields
    s = _TAG_RE.sub(' ', s)
    return ' '.join(s.split())


# ── Signature / initials / date / signedat block tokenisation ──────────────
#
# CTO audit (2026-05-12) found that every AI edit silently destroyed any
# existing SignatureBlock / InitialsBlock / DateBlock / SignedAtBlock TipTap
# nodes. Root cause: ``_strip_tags`` removes them on the way in (Claude never
# sees them) and ``_rebuild_html_from_lines`` / ``merge_lines_into_html``
# only emit ``<h*>/<p>/<li>/<hr>/<table>`` — the signature tags evaporate.
#
# Fix: before showing the document to Claude we replace each such tag with
# an opaque token (``⟪SIG#N⟫`` using non-HTML unicode brackets so it survives
# ``_strip_tags`` untouched). Claude sees the token as a magic string in the
# line text. After Claude returns, the round-trip helpers preserve tokens
# verbatim (they aren't HTML, don't match the merge-field mustache regex,
# and aren't recognised as anything else), and the view restores tokens to
# their original tag-with-attributes from the sidecar dict.
#
# Implicit-delete: if Claude omits a token from its output (intentionally
# removed the line, or restructured the doc), the corresponding signature
# block is dropped. That's the only way the AI can delete a signature block
# today — explicit insertion is the ``insert_signature_field`` tool below.
_SIG_TAGS = ("signature-field", "initials-field", "date-field", "signedat-field")
_SIG_BLOCK_RE = re.compile(
    r"<(" + "|".join(_SIG_TAGS) + r")\b[^>]*(?:/>|>.*?</\1>)",
    re.DOTALL | re.IGNORECASE,
)


def _extract_signature_tokens(html: str) -> tuple[str, dict]:
    """Replace each signature/initials/date/signedat-field tag with a
    positional opaque token. Returns ``(tokenised_html, sidecar)``.

    The sidecar maps each token to the verbatim original tag (with all
    attributes preserved — ``name``, ``role``, ``required``, ``style``,
    etc.). Token format ``⟪SIG#N⟫`` is deliberately non-HTML, so it
    travels through ``_strip_tags`` unchanged and Claude sees it as an
    opaque marker in the document text.
    """
    sidecar: dict[str, str] = {}
    counter = [0]

    def _stash(m: "re.Match[str]") -> str:
        token = f"⟪SIG#{counter[0]}⟫"
        sidecar[token] = m.group(0)
        counter[0] += 1
        return token

    new_html = _SIG_BLOCK_RE.sub(_stash, html)
    return new_html, sidecar


_SIG_DIMS_BY_TYPE = {
    "signature": ("signature-field", "width:200px;height:60px"),
    "initials":  ("initials-field",  "width:100px;height:40px"),
    "date":      ("date-field",      "width:120px;height:24px"),
    "signed_at": ("signedat-field",  "width:160px;height:24px"),
}


def _build_signature_field_html(field_type: str, signer_role: str, field_name: str = "") -> str:
    """Construct the canonical signing-field HTML span.

    Mirrors ``admin/src/extensions/SignatureBlockNode.ts::renderHTML`` so the
    output round-trips through TipTap's parseHTML without dropping attributes.
    The signing engine (``apps.esigning.services``) reads `name` + `role` to
    figure out who fills it in.
    """
    if field_type not in _SIG_DIMS_BY_TYPE:
        field_type = "signature"
    tag, dims = _SIG_DIMS_BY_TYPE[field_type]
    if not field_name:
        field_name = f"{signer_role}_{field_type}"
    style = f"display:inline-block;{dims};margin:4px 6px;vertical-align:middle;"
    fmt_attr = ' format="drawn_or_typed"' if field_type == "signature" else ""
    return (
        f'<{tag} name="{field_name}" role="{signer_role}" required="true" '
        f'style="{style}" data-field-type="{field_type}" '
        f'data-signer-role="{signer_role}" data-field-name="{field_name}"{fmt_attr}> </{tag}>'
    )


def _restore_signature_tokens(html: str, sidecar: dict) -> str:
    """Replace each ``⟪SIG#N⟫`` token with its original tag.

    Tokens still present in ``html`` are expanded back. Tokens missing
    from ``html`` (i.e. Claude removed them) are silently dropped — that's
    the intentional implicit-delete path. Tokens in ``html`` that aren't
    in the sidecar (shouldn't happen, but defensive) are stripped to keep
    the rendered output clean.
    """
    for token, original in (sidecar or {}).items():
        html = html.replace(token, original)
    # Defensive: any token-shaped artefact not in sidecar gets cleaned.
    # Runs even when sidecar is empty so stray tokens don't render to users.
    html = re.sub(r"⟪SIG#\d+⟫", "", html)
    return html


_STYLE_ATTR_RE = re.compile(r'\bstyle="([^"]*)"', re.IGNORECASE)

def _extract_style_props(attrs_str: str) -> dict:
    """
    Extract relevant inline style properties from an HTML attributes string.
    Returns a compact dict with only non-default/non-empty values.
    """
    m = _STYLE_ATTR_RE.search(attrs_str or '')
    if not m:
        return {}
    style = m.group(1)
    props = {}
    for decl in style.split(';'):
        decl = decl.strip()
        if ':' not in decl:
            continue
        k, _, v = decl.partition(':')
        k, v = k.strip().lower(), v.strip()
        if k == 'font-size' and v:
            props['fs'] = v          # e.g. "14pt", "1.2rem"
        elif k == 'font-family' and v:
            props['ff'] = v.split(',')[0].strip().strip('"\'')
        elif k == 'font-weight' and v not in ('normal', '400'):
            props['fw'] = v          # "bold" or "700"
        elif k == 'font-style' and v == 'italic':
            props['fi'] = True
        elif k == 'color' and v:
            props['fc'] = v
        elif k == 'text-align' and v not in ('left', 'start'):
            props['ta'] = v
        elif k == 'background-color' and v:
            props['bg'] = v
    return props


def _style_props_to_css(props: dict) -> str:
    """Convert style-props dict back to a CSS string."""
    css_map = {
        'fs': 'font-size', 'ff': 'font-family', 'fw': 'font-weight',
        'fi': 'font-style', 'fc': 'color', 'ta': 'text-align', 'bg': 'background-color',
    }
    parts = []
    for k, v in props.items():
        css_key = css_map.get(k)
        if not css_key:
            continue
        if k == 'fi':
            parts.append('font-style:italic')
        else:
            parts.append(f'{css_key}:{v}')
    return ';'.join(parts)


def html_to_doc_json(html: str) -> list:
    """
    Convert HTML → compact node list preserving inline formatting.
    Each node: { "i": int, "t": tag, "c": text_with_merge_fields, ...style_props }
    Style props (only present when non-default):
      fs=font-size, ff=font-family, fw=font-weight, fi=italic,
      fc=color, ta=text-align, bg=background-color
    """
    nodes = []
    i = 0
    for m in re.finditer(
        r'<(h1|h2|h3|h4|p|li|hr)([^>]*)>(.*?)</\1>|<hr\s*/?>',
        html, re.DOTALL | re.IGNORECASE
    ):
        tag = (m.group(1) or 'hr').lower()
        attrs = m.group(2) or ''
        inner = m.group(3) or ''
        text = _strip_tags(inner)
        if tag == 'hr' or text:
            node: dict = {'i': i, 't': tag, 'c': text}
            # Include inline style on the block element itself
            style_props = _extract_style_props(attrs)
            if style_props:
                node.update(style_props)
            # Also check first child span for font-size (common from contenteditable editors)
            if not style_props.get('fs'):
                first_span = re.search(r'<span([^>]*)>', inner, re.IGNORECASE)
                if first_span:
                    span_props = _extract_style_props(first_span.group(1))
                    if span_props.get('fs'):
                        node['fs'] = span_props['fs']
            nodes.append(node)
            i += 1
    return nodes


def doc_json_to_html(nodes: list) -> str:
    """Convert compact node list back to HTML, restoring inline styles."""
    SELF_CLOSE = {'hr'}
    parts = []
    for node in nodes:
        t = node.get('t', 'p')
        c = node.get('c', '').strip()
        # Restore merge field spans
        c = re.sub(
            r'\{\{\s*([\w]+)\s*\}\}',
            r'<span data-merge-field="\1">{{ \1 }}</span>',
            c
        )
        if t in SELF_CLOSE:
            parts.append('<hr>')
        else:
            style_props = {k: v for k, v in node.items() if k not in ('i', 't', 'c')}
            css = _style_props_to_css(style_props)
            style_attr = f' style="{css}"' if css else ''
            parts.append(f'<{t}{style_attr}>{c}</{t}>')
    return '\n'.join(parts)


def _doc_outline(nodes: list) -> str:
    """Return a compact section outline (h1/h2/h3 only) for context."""
    lines = []
    for n in nodes:
        if n['t'] in ('h1', 'h2', 'h3'):
            indent = {'h1': '', 'h2': '  ', 'h3': '    '}.get(n['t'], '')
            lines.append(f"{indent}[{n['i']}] {n['c']}")
    return '\n'.join(lines) if lines else '(no headings)'


_TABLE_CELL_RE = re.compile(r'<t[dh][^>]*>(.*?)</t[dh]>', re.DOTALL | re.IGNORECASE)
_TABLE_ROW_RE  = re.compile(r'<tr[^>]*>(.*?)</tr>', re.DOTALL | re.IGNORECASE)
_TABLE_RE      = re.compile(r'<table[^>]*>(.*?)</table>', re.DOTALL | re.IGNORECASE)


def _table_to_markdown(table_html: str) -> str:
    """Convert a <table>...</table> block to pipe-delimited markdown rows."""
    rows = []
    for row_m in _TABLE_ROW_RE.finditer(table_html):
        cells = [_strip_tags(c.group(1)) for c in _TABLE_CELL_RE.finditer(row_m.group(1))]
        rows.append('| ' + ' | '.join(cells) + ' |')
    return '\n'.join(rows)


def _markdown_to_table_html(md: str) -> str:
    """Convert pipe-delimited markdown rows back to a minimal HTML table."""
    lines = [l.strip() for l in md.strip().splitlines() if l.strip().startswith('|')]
    if not lines:
        return f'<p>{md}</p>'
    rows_html = []
    for i, line in enumerate(lines):
        cells = [c.strip() for c in line.strip('|').split('|')]
        tag = 'th' if i == 0 else 'td'
        rows_html.append('<tr>' + ''.join(f'<{tag}>{c}</{tag}>' for c in cells) + '</tr>')
    return '<table>' + ''.join(rows_html) + '</table>'


def html_to_plain_lines(html: str) -> list:
    """
    Strip HTML to plain numbered text lines — what Claude sees.
    Returns [{'i': int, 'tag': str, 'text': str}, ...]
    Merge fields kept as {{ field_name }}.
    Tables become pipe-delimited markdown (tag='table').
    All formatting/styling stripped — preserved in original HTML.
    """
    lines = []
    i = 0
    # First pass: replace <table>...</table> with a placeholder so block regex works
    table_placeholders = {}
    counter = [0]
    def _stash_table(m):
        key = f'__TABLE_{counter[0]}__'
        table_placeholders[key] = m.group(0)
        counter[0] += 1
        return f'<p>{key}</p>'
    patched = _TABLE_RE.sub(_stash_table, html)

    # Also stash page-break divs
    pb_re = re.compile(r'<div[^>]+data-page-break[^>]*>.*?</div>', re.DOTALL | re.IGNORECASE)
    patched2 = pb_re.sub('<p>__PAGE_BREAK__</p>', patched)

    for m in re.finditer(
        r'<(h1|h2|h3|h4|p|li|hr)([^>]*)>(.*?)</\1>|<hr\s*/?>',
        patched2, re.DOTALL | re.IGNORECASE
    ):
        tag = (m.group(1) or 'hr').lower()
        inner = m.group(3) or ''
        text = _strip_tags(inner).strip()
        if tag == 'hr':
            lines.append({'i': i, 'tag': 'hr', 'text': '---'})
            i += 1
        elif text == '__PAGE_BREAK__':
            lines.append({'i': i, 'tag': 'page_break', 'text': '=== PAGE BREAK ==='})
            i += 1
        elif text:
            placeholder_key = text.strip()
            if placeholder_key in table_placeholders:
                md = _table_to_markdown(table_placeholders[placeholder_key])
                lines.append({'i': i, 'tag': 'table', 'text': md})
            else:
                lines.append({'i': i, 'tag': tag, 'text': text})
            i += 1
    return lines


def plain_lines_to_text(lines: list) -> str:
    """
    Format plain lines as the text block Claude reads.
    H1/H2/H3 indented like a TOC, paragraph type shown in brackets.
    Tables shown as pipe-delimited markdown.
    """
    indent = {'h1': '', 'h2': '  ', 'h3': '    ', 'h4': '      '}
    parts = []
    for ln in lines:
        tag = ln['tag']
        prefix = indent.get(tag, '')
        if tag == 'hr':
            parts.append(f"[{ln['i']}] ---")
        elif tag == 'page_break':
            parts.append(f"[{ln['i']}] === PAGE BREAK ===")
        elif tag == 'table':
            parts.append(f"[{ln['i']}] [TABLE]\n{ln['text']}")
        elif tag in ('h1', 'h2', 'h3', 'h4'):
            parts.append(f"{prefix}[{ln['i']}] {ln['text']}")
        else:
            parts.append(f"[{ln['i']}] {ln['text']}")
    return '\n'.join(parts)


def merge_lines_into_html(original_html: str, edited_lines: list) -> str:
    """
    Splice edited text lines back into the original HTML, preserving all
    inline styles, attributes, and formatting.  Only text content changes.
    edited_lines: [{'i': int, 'text': str, 'tag': str?}]
    Tables: if tag=='table', text is pipe-delimited markdown → rebuilt as HTML table.
    """
    edits = {ln['i']: ln for ln in edited_lines}

    # Stash original tables so block-level regex can see them as single tokens
    table_originals = {}
    ctr = [0]
    def _stash(m):
        key = f'__TABLE_{ctr[0]}__'
        table_originals[key] = m.group(0)
        ctr[0] += 1
        return f'<p>{key}</p>'
    patched = _TABLE_RE.sub(_stash, original_html)

    result = []
    i = 0
    for m in re.finditer(
        r'(<(h1|h2|h3|h4|p|li|hr)([^>]*)>)(.*?)(</\2>)|(<hr\s*/?>)',
        patched, re.DOTALL | re.IGNORECASE
    ):
        if m.group(6):  # self-closing <hr>
            result.append(m.group(6))
            i += 1
            continue
        open_tag, tag, attrs, inner, close_tag = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
        text_content = _strip_tags(inner).strip()

        # Restore stashed table
        if text_content in table_originals:
            edit = edits.get(i)
            if edit and edit.get('tag') == 'table':
                result.append(_markdown_to_table_html(edit['text']))
            else:
                result.append(table_originals[text_content])
            i += 1
            continue

        if not text_content:
            result.append(m.group(0))
            continue

        edit = edits.get(i)
        if edit:
            new_text = edit['text']
            new_inner = re.sub(
                r'\{\{\s*([\w]+)\s*\}\}',
                r'<span data-merge-field="\1">{{ \1 }}</span>',
                new_text
            )
            result.append(f'{open_tag}{new_inner}{close_tag}')
        else:
            result.append(m.group(0))
        i += 1

    return '\n'.join(result) if result else original_html


def _rebuild_html_from_lines(original_html: str, lines: list) -> str:
    """
    Rebuild the full HTML document from a lines list, reusing original tag+style
    for lines that match by index, generating clean tags for new/changed lines.
    Used when update_all rewrites the document or edit_lines changes line count.
    """
    # Build a map of original open-tags by line index so we preserve inline styles
    orig_open_tags: dict = {}
    orig_close_tags: dict = {}
    i = 0
    for m in re.finditer(
        r'(<(h1|h2|h3|h4|p|li|hr)([^>]*)>)(.*?)(</\2>)|(<hr\s*/?>)',
        original_html, re.DOTALL | re.IGNORECASE
    ):
        if m.group(6):
            orig_open_tags[i] = m.group(6)
            orig_close_tags[i] = ''
        else:
            text_content = _strip_tags(m.group(4) or '').strip()
            if text_content or m.group(2).lower() == 'hr':
                orig_open_tags[i] = m.group(1)
                orig_close_tags[i] = m.group(5)
        i += 1

    parts = []
    for ln in lines:
        idx  = ln['i']
        tag  = ln.get('tag', 'p')
        text = ln.get('text', '')

        if tag == 'table':
            parts.append(_markdown_to_table_html(text))
            continue
        if tag == 'hr':
            parts.append('<hr>')
            continue
        if tag == 'page_break':
            parts.append('<p><br></p><div data-page-break="true" contenteditable="false"></div><p><br></p>')
            continue

        # Restore merge field spans in text
        inner = re.sub(
            r'\{\{\s*([\w]+)\s*\}\}',
            r'<span data-merge-field="\1">{{ \1 }}</span>',
            text
        )
        # Reuse original open/close tags if index matches and same tag type
        open_t  = orig_open_tags.get(idx, f'<{tag}>')
        close_t = orig_close_tags.get(idx, f'</{tag}>')
        # Verify tag type matches (e.g. don't apply <h1 style> to a <p>)
        orig_tag_match = re.match(r'<(\w+)', open_t)
        if orig_tag_match and orig_tag_match.group(1).lower() != tag.lower():
            open_t  = f'<{tag}>'
            close_t = f'</{tag}>'
        parts.append(f'{open_t}{inner}{close_t}')

    return '\n'.join(parts)


_XML_ESCAPE = str.maketrans({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'})

def doc_nodes_to_xml(nodes: list) -> str:
    """
    Render node list as clean XML — easy for Claude to read structure + content.
    Each element carries its node index as an attribute (i="N") so Claude can
    reference it precisely when calling edit tools.
    Merge fields are preserved as {{ field_name }} in the text.
    """
    STYLE_KEYS = {'fs', 'ff', 'fw', 'fi', 'fc', 'ta', 'bg'}
    lines = ['<doc>']
    for n in nodes:
        t = n.get('t', 'p')
        i = n.get('i', 0)
        c = n.get('c', '').translate(_XML_ESCAPE)
        # Inline style summary as XML attribute (brief, for quick reference)
        style_parts = []
        if n.get('fs'): style_parts.append(f"fs={n['fs']}")
        if n.get('ff'): style_parts.append(f"ff={n['ff']}")
        if n.get('fw'): style_parts.append(f"fw={n['fw']}")
        if n.get('fi'): style_parts.append('italic')
        if n.get('fc'): style_parts.append(f"color={n['fc']}")
        if n.get('ta'): style_parts.append(f"align={n['ta']}")
        if n.get('bg'): style_parts.append(f"bg={n['bg']}")
        style_attr = f' style="{", ".join(style_parts)}"' if style_parts else ''
        if t == 'hr':
            lines.append(f'  <hr i="{i}"/>')
        else:
            lines.append(f'  <{t} i="{i}"{style_attr}>{c}</{t}>')
    lines.append('</doc>')
    return '\n'.join(lines)


def doc_nodes_to_style_facts(nodes: list) -> list:
    """
    Extract only the style-bearing rows for the JSON fact table.
    Rows without any styling are omitted to keep the table compact.
    Schema: [{ i, fs?, ff?, fw?, fi?, fc?, ta?, bg? }, ...]
    """
    STYLE_KEYS = {'fs', 'ff', 'fw', 'fi', 'fc', 'ta', 'bg'}
    facts = []
    for n in nodes:
        style = {k: v for k, v in n.items() if k in STYLE_KEYS}
        if style:
            facts.append({'i': n['i'], **style})
    return facts


def _relevant_sections(nodes: list, query: str) -> list:
    """
    Cheap RAG: return only nodes whose section (h2 group) contains
    keywords from the query.  Always include h1 nodes for context.
    Falls back to all nodes if query is structural (restructure/format/all).
    """
    STRUCTURAL_WORDS = {'restructure', 'format', 'reformat', 'rewrite', 'all',
                        'sections', 'break', 'organise', 'organize', 'split',
                        'number', 'renumber', 'toc', 'contents', 'index'}
    q_words = set(re.findall(r'\w+', query.lower()))
    if q_words & STRUCTURAL_WORDS:
        return nodes  # structural request → need everything

    keywords = q_words - {'the', 'a', 'an', 'is', 'in', 'on', 'of', 'and',
                          'to', 'it', 'for', 'this', 'that', 'with', 'what',
                          'how', 'can', 'you', 'i', 'me', 'my', 'please', 'do'}

    # Group nodes into h2 sections; collect matching sections + all h1/h2 headings
    result_indices = set()
    current_section: list = []
    sections: list = []
    for n in nodes:
        if n['t'] == 'h2':
            if current_section:
                sections.append(current_section)
            current_section = [n]
        else:
            current_section.append(n)
    if current_section:
        sections.append(current_section)

    for sec in sections:
        sec_text = ' '.join(n['c'].lower() for n in sec)
        if any(kw in sec_text for kw in keywords):
            for n in sec:
                result_indices.add(n['i'])

    # Always include h1/h2 for structural awareness
    for n in nodes:
        if n['t'] in ('h1', 'h2'):
            result_indices.add(n['i'])

    selected = [n for n in nodes if n['i'] in result_indices]
    # If nothing matched at all, return full document
    return selected if selected else nodes


def _apply_formatting_to_html(html: str, from_i: int, to_i: int, style: dict) -> str:
    """
    Apply CSS inline-style properties to block elements in range [from_i, to_i].
    Existing styles are merged — new keys override, unspecified keys kept.
    style dict uses camelCase keys (fontSize, fontWeight, color, textAlign, etc.)
    """
    _camel_to_css = {
        'fontSize': 'font-size', 'fontFamily': 'font-family',
        'fontWeight': 'font-weight', 'fontStyle': 'font-style',
        'textDecoration': 'text-decoration', 'color': 'color',
        'backgroundColor': 'background-color', 'textAlign': 'text-align',
        'marginLeft': 'margin-left',
    }
    new_css = {_camel_to_css[k]: v for k, v in style.items() if k in _camel_to_css and v}
    if not new_css:
        return html

    parts = []
    cursor = 0
    i = 0
    for m in re.finditer(
        r'(<(h1|h2|h3|h4|p|li)([^>]*)>)(.*?)(</\2>)',
        html, re.DOTALL | re.IGNORECASE
    ):
        tag, attrs, inner, close_tag = m.group(2), m.group(3), m.group(4), m.group(5)
        text_content = _strip_tags(inner).strip()
        if not text_content:
            continue  # skip empty, don't count index
        parts.append(html[cursor:m.start()])
        if from_i <= i <= to_i:
            existing: dict = {}
            style_m = _STYLE_ATTR_RE.search(attrs)
            if style_m:
                for decl in style_m.group(1).split(';'):
                    decl = decl.strip()
                    if ':' in decl:
                        k, _, v = decl.partition(':')
                        existing[k.strip().lower()] = v.strip()
            merged = {**existing, **new_css}
            css_str = ';'.join(f'{k}:{v}' for k, v in merged.items() if v)
            new_attrs = _STYLE_ATTR_RE.sub('', attrs).strip()
            parts.append(f'<{tag}{(" " + new_attrs) if new_attrs else ""} style="{css_str}">{inner}</{tag}>')
        else:
            parts.append(m.group(0))
        cursor = m.end()
        i += 1

    parts.append(html[cursor:])
    return ''.join(parts)


def _build_toc_html(html: str, title: str = "TABLE OF CONTENTS") -> str:
    headings = re.findall(r'<h2[^>]*>(.*?)</h2>', html, re.DOTALL)
    if not headings:
        return ""
    items = "".join(f"<li>{h}</li>" for h in headings)
    return f'<div data-block-comment="toc"><strong>{title}</strong><ol>{items}</ol></div>'


def _renumber_headings(html: str, style: str = "number_dot", levels: str = "h2_h3_h4",
                       renumber_paragraphs: bool = True) -> str:
    """
    Multi-level heading AND paragraph renumbering.

    Headings (h2/h3/h4) get sequential numbers: 1. / 1.1 / 1.1.1
    Paragraphs that already start with a number prefix (e.g. "3.1.", "9.2.1.")
    get renumbered to match their parent section.

    levels:
      "h2"          — only h2:  1. 2. 3.
      "h2_h3"       — h2+h3:   1. / 1.1 / 1.2
      "h2_h3_h4"    — all:     1. / 1.1 / 1.1.1

    style:
      "number_dot"  — "1. ", "1.1 ", "1.1.1 "
      "number_only" — "1 ", "1.1 ", "1.1.1 "

    renumber_paragraphs:
      If True, also renumber <p> elements that start with number prefixes
      (e.g. "3.1. The Lessor..." becomes "4.1. The Lessor..." if section moved).
    """
    _NUM_PREFIX = re.compile(r'^[\d]+(?:\.[\d]+)*\.?\s*')
    # Match numbered paragraphs: "3.1.", "9.2.1.", "11.1.15." etc.
    _P_NUM_RE = re.compile(r'^(\d+(?:\.\d+)+)\.?\s+')

    target_tags = {"h2"}
    if levels in ("h2_h3", "h2_h3_h4"):
        target_tags.add("h3")
    if levels == "h2_h3_h4":
        target_tags.add("h4")

    # State tracking
    h2_counter = [0]
    h3_counter = [0]
    h4_counter = [0]
    p_counter = [0]       # paragraph counter within current section scope
    h2_p_count = [0]      # numbered paragraphs seen directly under h2 (before any h3)
    h3_p_count = [0]      # numbered paragraphs seen directly under h3 (before any h4)
    current_depth = [0]   # 1=under h2, 2=under h3, 3=under h4

    def process_element(m):
        full_match = m.group(0)
        tag_name = m.group(2).lower()
        attrs = m.group(3)
        inner = m.group(4)

        # Handle headings
        if tag_name in ("h2", "h3", "h4"):
            if tag_name not in target_tags:
                return full_match

            sep = ". " if style == "number_dot" else " "

            if tag_name == "h2":
                h2_counter[0] += 1
                h3_counter[0] = 0
                h4_counter[0] = 0
                p_counter[0] = 0
                h2_p_count[0] = 0
                h3_p_count[0] = 0
                current_depth[0] = 1
                prefix = f"{h2_counter[0]}"
            elif tag_name == "h3":
                # h3 continues the sub-numbering after any direct h2 paragraphs
                # e.g. if h2 had paragraphs 5.1., then first h3 = 5.2
                if h3_counter[0] == 0 and h2_p_count[0] > 0:
                    h3_counter[0] = h2_p_count[0] + 1
                else:
                    h3_counter[0] += 1
                h4_counter[0] = 0
                p_counter[0] = 0
                h3_p_count[0] = 0
                current_depth[0] = 2
                prefix = f"{h2_counter[0]}.{h3_counter[0]}"
            else:  # h4
                # Same logic: h4 continues after any direct h3 paragraphs
                if h4_counter[0] == 0 and h3_p_count[0] > 0:
                    h4_counter[0] = h3_p_count[0] + 1
                else:
                    h4_counter[0] += 1
                p_counter[0] = 0
                current_depth[0] = 3
                prefix = f"{h2_counter[0]}.{h3_counter[0]}.{h4_counter[0]}"

            # Strip existing number prefix from inner HTML
            cleaned_inner = re.sub(r'^(\s*)[\d]+(?:\.[\d]+)*\.?\s*', r'\1', inner.lstrip()).lstrip()
            return f"<{tag_name}{attrs}>{prefix}{sep}{cleaned_inner}</{tag_name}>"

        # Handle paragraphs
        if tag_name == "p" and renumber_paragraphs:
            text = _strip_tags(inner).strip()
            # Skip empty paragraphs or paragraphs that are ONLY a number prefix
            if not text or text.replace('.', '').replace(' ', '').isdigit():
                return full_match
            p_match = _P_NUM_RE.match(text)
            if p_match:
                old_num = p_match.group(1)
                p_counter[0] += 1

                # Build new prefix based on current section depth
                if current_depth[0] == 1:
                    # Under h2: "3.1.", "3.2." etc.
                    h2_p_count[0] = p_counter[0]
                    new_num = f"{h2_counter[0]}.{p_counter[0]}"
                elif current_depth[0] == 2:
                    # Under h3: "5.2.1.", "5.2.2." etc.
                    h3_p_count[0] = p_counter[0]
                    new_num = f"{h2_counter[0]}.{h3_counter[0]}.{p_counter[0]}"
                elif current_depth[0] == 3:
                    # Under h4: "5.2.1.1.", "5.2.1.2." etc.
                    new_num = f"{h2_counter[0]}.{h3_counter[0]}.{h4_counter[0]}.{p_counter[0]}"
                else:
                    return full_match

                # Replace old number in inner HTML preserving formatting
                escaped_old = re.escape(old_num)
                new_inner = re.sub(
                    rf'{escaped_old}\.?\s+',
                    f'{new_num}. ',
                    inner,
                    count=1
                )
                return f"<{tag_name}{attrs}>{new_inner}</{tag_name}>"

        return full_match

    return re.sub(
        r'(<(h[234]|p)([^>]*)>(.*?)</\2>)',
        process_element,
        html,
        flags=re.DOTALL | re.IGNORECASE
    )


def _insert_comment_html(html: str, comment: str, position: str, after_heading: str = "") -> str:
    block = f'<div data-block-comment="">{comment}</div>'
    if position == "start":
        return block + html
    if position == "after_section" and after_heading:
        pat = rf'(<h2[^>]*>{re.escape(after_heading)}[^<]*</h2>)'
        new = re.sub(pat, r'\1' + block, html, count=1, flags=re.IGNORECASE)
        return new if new != html else html + block
    return html + block


# ── Skill helpers ─────────────────────────────────────────────────────────

_SA_STANDARD_SECTIONS = [
    ("PARTIES", ["parties", "landlord", "tenant", "lessor", "lessee"]),
    ("PREMISES", ["premises", "property", "address"]),
    ("LEASE PERIOD", ["lease period", "term", "duration", "commencement"]),
    ("RENTAL AND DEPOSIT", ["rent", "deposit", "payment", "banking"]),
    ("UTILITIES", ["utilities", "water", "electricity", "municipal"]),
    ("OCCUPANCY", ["occupancy", "occupant", "household"]),
    ("MAINTENANCE AND REPAIRS", ["maintenance", "repair"]),
    ("INSPECTIONS", ["inspection", "ingoing", "outgoing"]),
    ("NOTICE AND TERMINATION", ["notice", "termination", "cancellation", "breach"]),
    ("CONSUMER PROTECTION ACT", ["consumer protection", "cpa"]),
    ("PROTECTION OF PERSONAL INFORMATION", ["popia", "personal information", "data protection"]),
    ("DISPUTE RESOLUTION", ["dispute", "tribunal", "mediation", "arbitration"]),
    ("SIGNATURES", ["signature", "witness", "signatory"]),
]

_RHA_MANDATORY_KEYWORDS = [
    ("Deposit in interest-bearing account", ["interest-bearing", "interest bearing"]),
    ("Deposit refund within 14 days", ["14 days", "fourteen days", "refund"]),
    ("Minimum notice period", ["notice period", "calendar month", "20 business days"]),
    ("Habitable premises obligation", ["habitable", "fit for habitation"]),
    ("CPA fixed-term compliance", ["consumer protection", "cpa", "act 68"]),
    ("POPIA data consent", ["popia", "personal information", "act 4 of 2013"]),
    ("Rental Housing Tribunal", ["tribunal", "rental housing act"]),
]


def _check_rha_compliance(html: str) -> dict:
    """Check template HTML against SA Rental Housing Act requirements."""
    html_lower = html.lower()

    # Extract h2/h3 headings
    headings = [m.group(1).lower() for m in re.finditer(r'<h[23][^>]*>(.*?)</h[23]>', html, re.I)]
    headings_text = " ".join(headings)

    # Check standard sections
    sections_found = []
    sections_missing = []
    for section_name, keywords in _SA_STANDARD_SECTIONS:
        found = any(kw in headings_text for kw in keywords)
        if found:
            sections_found.append(section_name)
        else:
            sections_missing.append(section_name)

    # Check mandatory clauses in full body
    clauses_found = []
    clauses_missing = []
    for clause_name, keywords in _RHA_MANDATORY_KEYWORDS:
        found = any(kw in html_lower for kw in keywords)
        if found:
            clauses_found.append(clause_name)
        else:
            clauses_missing.append(clause_name)

    total = len(_SA_STANDARD_SECTIONS) + len(_RHA_MANDATORY_KEYWORDS)
    passed = len(sections_found) + len(clauses_found)

    # Build summary
    lines = [f"RHA Compliance: {passed}/{total} checks passed.\n"]
    if sections_missing:
        lines.append(f"Missing sections: {', '.join(sections_missing)}")
    if clauses_missing:
        lines.append(f"Missing clauses: {', '.join(clauses_missing)}")
    if not sections_missing and not clauses_missing:
        lines.append("All standard sections and mandatory clauses are present.")

    return {
        "pass_count": passed,
        "total_checks": total,
        "sections_found": sections_found,
        "sections_missing": sections_missing,
        "clauses_found": clauses_found,
        "clauses_missing": clauses_missing,
        "summary": "\n".join(lines),
    }


def _format_sa_standard(html: str, add_missing: bool = True, preserve_custom: bool = True) -> str:
    """Add missing standard SA lease sections without reordering existing content.

    Preserves the original document order and only appends missing
    standard sections before the final Signatures/Signatories section.
    """
    # Split into sections by h2
    parts = re.split(r'(?=<h2[^>]*>)', html, flags=re.I)
    preamble = parts[0] if parts else ""
    sections = parts[1:] if len(parts) > 1 else []

    # Identify which standard sections already exist
    present: set[str] = set()
    for section_html in sections:
        heading_match = re.search(r'<h2[^>]*>(.*?)</h2>', section_html, re.I)
        if not heading_match:
            continue
        heading_text = heading_match.group(1).lower()
        for standard_name, keywords in _SA_STANDARD_SECTIONS:
            if any(kw in heading_text for kw in keywords):
                present.add(standard_name)
                break

    if not add_missing:
        return html

    # Build list of missing sections
    missing_sections = []
    for standard_name, _ in _SA_STANDARD_SECTIONS:
        if standard_name not in present:
            missing_sections.append(
                f'<h2>{standard_name}</h2>\n'
                f'<p><em>[This section needs to be completed]</em></p>\n'
            )

    if not missing_sections:
        return html

    # Insert missing sections before the last section if it's Signatures/Signatories
    if sections:
        last_heading = re.search(r'<h2[^>]*>(.*?)</h2>', sections[-1], re.I)
        last_text = (last_heading.group(1).lower() if last_heading else "")
        if any(kw in last_text for kw in ["signature", "signatory", "signatories"]):
            result_parts = [preamble] + sections[:-1] + missing_sections + [sections[-1]]
            return "\n".join(result_parts)

    # Otherwise append at end
    result_parts = [preamble] + sections + missing_sections
    return "\n".join(result_parts)


# ── Tool definitions for document editing ─────────────────────────────────
_TEMPLATE_TOOLS = [
    {
        "name": "edit_lines",
        "description": (
            "Edit specific lines by index range. "
            "Use for any targeted text edit: rewrite a clause, fix wording, add/remove paragraphs in a section. "
            "Plain text only — formatting is preserved from the original document. "
            "Merge fields: keep as {{ field_name }}."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "from_index": {"type": "integer", "description": "First line index to replace (inclusive)."},
                "to_index":   {"type": "integer", "description": "Last line index to replace (inclusive)."},
                "new_lines": {
                    "type": "array",
                    "description": "Replacement lines. Each: {\"tag\": \"h1|h2|h3|p|li|hr\", \"text\": \"plain text\"}. No HTML tags in text.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "tag":  {"type": "string", "enum": ["h1","h2","h3","h4","p","li","hr"]},
                            "text": {"type": "string"}
                        },
                        "required": ["tag", "text"]
                    }
                },
                "summary": {"type": "string", "description": "One sentence describing what changed."}
            },
            "required": ["from_index", "to_index", "new_lines", "summary"]
        }
    },
    {
        "name": "update_all",
        "description": (
            "Rewrite or restructure the entire document. "
            "Use only when adding/removing/reordering multiple sections. "
            "Returns all lines — plain text, no HTML, preserve {{ field_name }} merge fields."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lines": {
                    "type": "array",
                    "description": "Complete ordered line list for the whole document.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "tag":  {"type": "string", "enum": ["h1","h2","h3","h4","p","li","hr"]},
                            "text": {"type": "string"}
                        },
                        "required": ["tag", "text"]
                    }
                },
                "summary": {"type": "string"}
            },
            "required": ["lines", "summary"]
        }
    },
    {
        "name": "add_comment",
        "description": "Insert a visible AI annotation/comment block. Use to flag issues, explain clauses, or leave review notes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "comment":       {"type": "string"},
                "position":      {"type": "string", "enum": ["start", "end", "after_section"]},
                "after_heading": {"type": "string", "description": "Heading text to insert after (position=after_section only)."}
            },
            "required": ["comment", "position"]
        }
    },
    {
        "name": "insert_toc",
        "description": "Generate and insert a Table of Contents from h2 headings.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "TOC heading (default: TABLE OF CONTENTS)"}
            },
            "required": []
        }
    },
    {
        "name": "renumber_sections",
        "description": (
            "Renumber headings AND clause paragraphs with multi-level numbering. "
            "Headings: h2 (1.), h3 (1.1), h4 (1.1.1). "
            "Paragraphs: clauses starting with numbers like '3.1.', '9.2.1.' get renumbered to match their parent section. "
            "Use when sections have been reordered, added, or removed and numbering is out of sync."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "style": {"type": "string", "enum": ["number_dot", "number_only"], "description": "Separator after number. Default: number_dot"},
                "levels": {"type": "string", "enum": ["h2", "h2_h3", "h2_h3_h4"], "description": "Which heading levels to number. Default: h2_h3_h4"},
                "renumber_paragraphs": {"type": "boolean", "description": "Also renumber numbered paragraphs/clauses (e.g. 3.1., 9.2.1.). Default: true"}
            },
            "required": []
        }
    },
    {
        "name": "highlight_fields",
        "description": "Flash specific merge field chips in the editor so the user can see where a variable appears.",
        "input_schema": {
            "type": "object",
            "properties": {
                "field_names": {"type": "array", "items": {"type": "string"}},
                "message":     {"type": "string"}
            },
            "required": ["field_names", "message"]
        }
    },
    {
        "name": "apply_formatting",
        "description": (
            "Apply inline styling to specific lines by index — without changing text. "
            "Use for: changing font size, family, weight, color, alignment, or indentation. "
            "Can target a single line or a range. "
            "Only provide the style properties you want to change; others are left untouched."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "from_index": {"type": "integer", "description": "First line index to style (inclusive)."},
                "to_index":   {"type": "integer", "description": "Last line index to style (inclusive). Same as from_index for a single line."},
                "style": {
                    "type": "object",
                    "description": "CSS style properties to apply. Use camelCase keys.",
                    "properties": {
                        "fontSize":     {"type": "string", "description": "e.g. '12pt', '1rem'"},
                        "fontFamily":   {"type": "string", "description": "e.g. 'Arial', 'Georgia'"},
                        "fontWeight":   {"type": "string", "description": "'bold' or 'normal'"},
                        "fontStyle":    {"type": "string", "description": "'italic' or 'normal'"},
                        "textDecoration":{"type": "string","description": "'underline' or 'none'"},
                        "color":        {"type": "string", "description": "hex color e.g. '#1e3a5f'"},
                        "backgroundColor":{"type":"string","description": "hex color"},
                        "textAlign":    {"type": "string", "enum": ["left","center","right","justify"]},
                        "marginLeft":   {"type": "string", "description": "indentation e.g. '24px'"},
                    }
                },
                "summary": {"type": "string", "description": "One sentence describing the change."}
            },
            "required": ["from_index", "to_index", "style", "summary"]
        }
    },
    # ── Skill-based tools ──
    {
        "name": "check_rha_compliance",
        "description": (
            "Audit the current template for South African Rental Housing Act compliance. "
            "Checks for 13 standard sections and 7 mandatory clauses (deposit terms, notice period, "
            "POPIA, CPA, dispute resolution, habitable premises, Rental Housing Tribunal). "
            "Returns a compliance report. Use when the user asks about compliance, legality, "
            "missing clauses, or 'is this lease valid'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "format_sa_standard",
        "description": (
            "Restructure the entire template to match the standard 13-section South African lease format. "
            "Reorders existing sections to the standard order, adds placeholder sections for any missing "
            "standard sections, and preserves custom sections at the end. "
            "Use when asked to 'format as standard SA lease', 'restructure', or 'add missing sections'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "add_missing_sections": {
                    "type": "boolean",
                    "description": "If true, add placeholder sections for any missing standard sections. Default true."
                },
                "preserve_custom_sections": {
                    "type": "boolean",
                    "description": "If true, keep non-standard sections at the end. Default true."
                }
            },
            "required": []
        }
    },
    {
        "name": "insert_signature_field",
        "description": (
            "Insert a SignatureBlock atomic node into the document. Use this when the user "
            "asks you to ADD a signature, initials, date-signed, or signed-at field for a "
            "specific actor. The new block becomes an interactive fillable widget when the "
            "lease is sent to signers.\n\n"
            "Only call this when the user explicitly asks for a signature/initials/date field, "
            "and only for actors they specifically named (landlord, tenant_1, tenant_2, "
            "witness, agent). NEVER bulk-insert signature blocks across the document during a "
            "restructure — that's noisy. To remove existing signature blocks, omit their "
            "⟪SIG#N⟫ token from your edit_lines / update_all output."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "after_line_index": {
                    "type": "integer",
                    "description": (
                        "The block is appended to the END of this line (paragraph). "
                        "Use the [N] index from the document text view. If you want "
                        "the block on its own line, call edit_lines first to insert "
                        "a label paragraph (e.g. 'Landlord signature:'), then call "
                        "this with that line's index."
                    ),
                },
                "field_type": {
                    "type": "string",
                    "enum": ["signature", "initials", "date", "signed_at"],
                    "description": (
                        "signature = full pad (drawn or typed). initials = small pad. "
                        "date = auto-filled date at signing. signed_at = location/place."
                    ),
                },
                "signer_role": {
                    "type": "string",
                    "enum": ["landlord", "tenant_1", "tenant_2", "tenant_3",
                             "witness_1", "witness_2", "agent", "occupant_1"],
                    "description": (
                        "Which signer the block belongs to. Use tenant_1 for the primary "
                        "tenant (most leases). Default to landlord/tenant_1 pairs unless "
                        "the user explicitly names additional parties."
                    ),
                },
                "field_name": {
                    "type": "string",
                    "description": (
                        "Optional unique field name. If omitted, auto-generated as "
                        "<role>_<type> (e.g. landlord_signature, tenant_1_initials). "
                        "Useful when inserting multiple initials per party (e.g. "
                        "'landlord_initials_p2' for page 2)."
                    ),
                },
            },
            "required": ["after_line_index", "field_type", "signer_role"],
        },
    },
]


class LeaseTemplateAIChatView(APIView):
    """
    POST /api/v1/leases/templates/{id}/ai-chat/

    Always sends the full document to Claude as XML (content + structure)
    + a compact JSON style fact-table (formatting props indexed by node i).
    Claude picks the right tool; nodes are converted back to HTML for storage.
    """
    permission_classes = [IsAgentOrAdmin]

    def post(self, request, pk):
        import anthropic
        from django.conf import settings

        try:
            tmpl = _scoped_lease_templates(request).get(pk=pk)
        except LeaseTemplate.DoesNotExist:
            return Response({"error": "Template not found."}, status=status.HTTP_404_NOT_FOUND)

        user_message = (request.data.get("message") or "").strip()
        if not user_message:
            return Response({"error": "message is required."}, status=status.HTTP_400_BAD_REQUEST)

        # api_history is the full Claude conversation stored by the frontend.
        # On the first message it's absent; we build it from the document.
        # On subsequent messages it already contains the document context.
        api_history = request.data.get("api_history") or []

        from apps.leases.merge_fields import build_merge_fields_prompt_block, CANONICAL_FIELD_NAMES

        current_html = _extract_html(tmpl.content_html)
        # Tokenise signature/initials/date/signedat blocks BEFORE Claude sees
        # the document. Claude can preserve them by keeping ⟪SIG#N⟫ tokens in
        # its output, or implicitly delete them by omitting the token. The
        # round-trip helpers (html_to_plain_lines / merge_lines_into_html /
        # _rebuild_html_from_lines) would otherwise strip the tags silently —
        # destroying every signature block on every AI edit (CTO audit P0).
        current_html, sig_sidecar = _extract_signature_tokens(current_html)
        detected = _detect_fields_from_html(current_html)
        detected_valid   = [f for f in detected if f in CANONICAL_FIELD_NAMES]
        detected_invalid = [f for f in detected if f not in CANONICAL_FIELD_NAMES]
        used_info = ", ".join(detected_valid) if detected_valid else "none yet"
        fields_block = build_merge_fields_prompt_block()

        invalid_warning = ""
        if detected_invalid:
            invalid_warning = (
                "\n⚠️  INVALID fields currently in the document (these are NOT in the Available list "
                "— replace them with the correct canonical names): "
                + ", ".join(detected_invalid) + "\n"
            )

        system = (
            f"You are an expert South African residential lease template advisor.\n"
            f"Template: \"{tmpl.name}\"\n\n"
            f"{fields_block}\n\n"
            f"Canonical fields used in this document: {used_info}"
            f"{invalid_warning}\n"
            "## CRITICAL FIELD RULES\n"
            "- ONLY use merge field names from the 'Available Merge Fields' list above. "
            "NEVER invent, pluralise, rename, or extend field names.\n"
            "- **DEFAULT TO ONE TENANT.** Use `tenant_name`, `tenant_id`, `tenant_email`, "
            "`tenant_phone` only — do NOT auto-populate `tenant_2_*`/`tenant_3_*` "
            "or `occupant_2/3/4_*` when restructuring. Only add the second/third tenant slots "
            "when the user explicitly says 'co-tenant', 'second tenant', or names additional "
            "tenants. If unsure, ASK the user how many tenants this lease has.\n"
            "- Common mistakes to AVOID: `landlord_full_name` (use `landlord_name`), "
            "`tenant_full_name` (use `tenant_name`), `monthly_rental` (use `monthly_rent`), "
            "`property_suburb`/`property_postal_code` (not available — use `property_address` "
            "or `city`/`province`), `authorised_occupants` (use `occupant_1_name`, `occupant_2_name`, etc.), "
            "`landlord_address` (use `landlord_physical_address`), `landlord_contact_number` "
            "(use `landlord_contact` or `landlord_phone`), `bank_name`/`account_number` "
            "(use `landlord_bank_name`/`landlord_bank_account_no`), `payment_due_day`/`escalation_percentage`/"
            "`late_payment_penalty` (not available — write these as literal numbers agreed with the landlord), "
            "`lease_start_date` (use `lease_start`), `lease_end_date` (use `lease_end`).\n"
            "- If a concept you want to express has no canonical field, write it as LITERAL TEXT "
            "(e.g. 'Signed at ___________' with a blank) — never invent a new {{ field_name }}.\n"
            "- If the user asks 'what fields are available?', list fields from the Available Merge Fields "
            "block above verbatim — do NOT read them from the document.\n\n"
            "Write fields as {{ field_name }} in text.\n\n"
            "## Document Format\n"
            "The document is provided as numbered plain-text lines:\n"
            "  [0] h1 heading text\n"
            "    [1] h2 subheading\n"
            "  [5] paragraph or list item text\n"
            "  [8] [TABLE]\n"
            "  | Col A | Col B |\n"
            "  | value | value |\n\n"
            "Line numbers are the `i` index you use when calling edit tools.\n"
            "Merge fields appear as {{ field_name }} — preserve them exactly.\n"
            "Formatting (font, size, colour) is stored separately — do NOT include HTML in text.\n\n"
            "## Tools — pick the right one\n\n"
            "### Editing Tools\n"
            "- **edit_lines** — replace text in a range of lines (preferred for targeted edits)\n"
            "- **update_all** — rewrite the entire document (only for large restructures)\n"
            "- **apply_formatting** — change font, size, color, alignment, bold etc on lines by index WITHOUT changing text\n"
            "- **insert_toc** — insert a table of contents from h2 headings\n"
            "- **renumber_sections** — multi-level heading renumbering (h2, h2+h3, or h2+h3+h4). Preserves the template's numbering depth.\n"
            "- **add_comment** — insert an annotation block\n"
            "- **highlight_fields** — flag specific merge field variables\n\n"
            "### Skill Tools\n"
            "- **check_rha_compliance** — audit this template against SA Rental Housing Act requirements (13 standard sections + 7 mandatory clauses)\n"
            "- **format_sa_standard** — restructure the entire template to the standard 13-section SA lease format\n\n"
            "### External Skills (mention to user when relevant)\n"
            "- **Parse Lease Contract** — import a PDF/DOCX contract as a template. Direct user to the Import wizard on the Templates page.\n"
            "- **E-Signing (native)** — send for signing, manage signers, track status. Klikk uses NATIVE e-signing (the legacy DocuSeal integration was removed in April 2026). The signing wizard lives on the lease detail page; signers receive an emailed link, sign in the browser, and the signed PDF is generated server-side.\n\n"

            "## Signature, Initials, Date, and Signed-At Fields\n"
            "Signature blocks are TipTap atomic nodes that render as fillable widgets in the final PDF.\n"
            "\n"
            "**In your text view they appear as `⟪SIG#0⟫`, `⟪SIG#1⟫`, etc. — opaque tokens you must treat as magic strings.**\n"
            "\n"
            "Rules:\n"
            "  • To **preserve** a signature block when editing its line: keep the `⟪SIG#N⟫` token in your new text, in the same approximate position. Don't rewrite, renumber, or reformat the tokens.\n"
            "  • To **remove** a signature block (e.g. user says 'no need for witnesses to sign'): simply omit that token from your new line text. The block is dropped silently and cleanly.\n"
            "  • To **insert a new** signature block: call the `insert_signature_field` tool with the line index and signer role. You CANNOT invent a new token (`⟪SIG#99⟫`) inside text — only `insert_signature_field` can create them.\n"
            "  • NEVER write signature fields as merge-field mustaches (`{{ landlord_signature }}`) or as bracketed placeholders (`[Signature: ___]`) — these won't render as fillable widgets.\n"
            "\n"
            "If the user says 'this lease only needs landlord and tenant to sign, no witnesses', identify the witness `⟪SIG#N⟫` tokens in the document (their owning paragraphs usually have witness labels nearby) and omit those tokens in your edit_lines / update_all replacement text. Then use `insert_signature_field` for any missing landlord/tenant blocks.\n\n"
            "## SA Rental Law Quick Reference\n"
            "Mandatory clauses per RHA 50/1999, CPA 68/2008, POPIA 4/2013:\n"
            "- Deposit in interest-bearing account (s5(3)(f) RHA)\n"
            "- Deposit refund within 14 days of termination (s5(3)(h) RHA)\n"
            "- Minimum notice: one calendar month / 20 business days (s5(3)(c) RHA)\n"
            "- Landlord must maintain habitable premises (s5A RHA)\n"
            "- CPA s14 compliance for fixed-term agreements\n"
            "- POPIA data processing consent clause\n"
            "- Dispute resolution via Rental Housing Tribunal (s13 RHA)\n\n"
            "Standard 13-section structure: PARTIES · PREMISES · LEASE PERIOD · RENTAL AND DEPOSIT · "
            "UTILITIES · OCCUPANCY · MAINTENANCE AND REPAIRS · INSPECTIONS · NOTICE AND TERMINATION · "
            "CONSUMER PROTECTION ACT · POPIA · DISPUTE RESOLUTION · SIGNATURES\n\n"
            "Rules:\n"
            "- Always call a tool for any edit/format request — never just describe changes\n"
            "- Text content only in edit_lines/update_all: plain text + {{ field_name }}, no HTML tags\n"
            "- For formatting requests (bold, font size, color, alignment): use apply_formatting with line indices\n"
            "- For tables use tag='table', text = pipe-delimited markdown rows\n"
            "- Prefer edit_lines over update_all unless moving/adding/removing many sections\n"
            "- Keep conversational replies ≤ 3 sentences\n"
            "- When mentioning which tools you used, be specific about what each tool did"
        )

        if api_history:
            api_messages = api_history + [{"role": "user", "content": user_message}]
        else:
            # First message — build plain-text document context
            plain_lines = html_to_plain_lines(current_html) if current_html else []
            doc_text    = plain_lines_to_text(plain_lines) if plain_lines else "(empty document)"
            doc_context = (
                f"Full document — {len(plain_lines)} lines:\n\n"
                f"{doc_text}"
            )
            api_messages = [
                {"role": "user",      "content": doc_context},
                {"role": "assistant", "content": "Understood. I have the full document. How can I help?"},
                {"role": "user",      "content": user_message},
            ]

        try:
            api_key = _get_anthropic_api_key()
            if not api_key:
                return Response({"error": "ANTHROPIC_API_KEY is not configured on the server."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            client = anthropic.Anthropic(api_key=api_key, timeout=120.0)

            reply_parts = []
            document_update = None
            field_highlight = None
            tools_used = []
            # AI #4 fix — track unknown tool names so the final reply tells
            # the user something concrete instead of silently saying "Done."
            unknown_tool_attempts: list[str] = []

            # AI #3 (P0) — multi-turn tool loop. The previous one-shot dispatch
            # meant Claude could only call ONE tool per user message; chained
            # work like "audit this and fix any issues" had to be split across
            # several follow-up messages (the audit tool ran, but Claude never
            # saw the report, so couldn't decide what to fix). Now we feed
            # tool_result blocks back and let Claude continue for up to
            # MAX_TURNS before stopping. Bound MAX_TURNS to cap latency + cost.
            MAX_TURNS = 4
            response = None
            for turn in range(MAX_TURNS):
                response = client.messages.create(
                    model=getattr(__import__('django.conf', fromlist=['settings']).settings, 'ANTHROPIC_MODEL_LEASE_CHAT', None) or "claude-sonnet-4-5",
                    max_tokens=32000,
                    system=system,
                    tools=_TEMPLATE_TOOLS,
                    messages=api_messages,
                )

                # AI #9 — Handle max_tokens truncation gracefully. Bumped
                # max_tokens from 16k → 32k above; this is the fallback for
                # truly oversized documents.
                if getattr(response, 'stop_reason', None) == 'max_tokens':
                    logger.warning(
                        "Lease AI hit max_tokens cap (template=%s, turn=%d); user message: %r",
                        pk, turn, user_message[:200] if user_message else None,
                    )
                    return Response({
                        "reply": (
                            "The document is too large to rewrite in one go. Try asking "
                            "for a specific section (e.g. 'rewrite section 3' or 'add a "
                            "POPIA clause after the deposit section') instead of a full "
                            "restructure. For very large templates, the format_sa_standard "
                            "skill works incrementally."
                        ),
                        "document_update": None,
                    })

                turn_tool_uses = []   # raw blocks to feed back as assistant turn
                turn_tool_results = []   # tool_result blocks for next user turn

                for block in response.content:
                    if block.type == "text" and block.text.strip():
                        reply_parts.append(block.text.strip())

                    elif block.type == "tool_use":
                        name = block.name
                        inp  = block.input
                        # AI #3: track this tool_use so we can feed a tool_result
                        # back to Claude in the next turn. result_summary is the
                        # text Claude sees as the tool's output — keep it short
                        # (Claude doesn't need the full document, just the
                        # outcome of its tool call).
                        turn_tool_uses.append(block)
                        result_summary = "OK"

                        # Helper: save edited (tokenised) HTML to DB after
                        # restoring signature blocks, and emit the restored form
                        # to the frontend. Keeps `current_html` tokenised for
                        # downstream tools (if Claude chains multiple in one
                        # turn, which is rare today but cheap to support).
                        def _persist(new_html_tokenised: str, summary: str) -> str:
                            restored = _restore_signature_tokens(new_html_tokenised, sig_sidecar)
                            tmpl.content_html = restored
                            tmpl.save(update_fields=["content_html"])
                            return restored

                        if name == "edit_lines":
                            from_i    = int(inp.get("from_index", 0))
                            to_i      = int(inp.get("to_index", from_i))
                            new_lines = inp.get("new_lines", [])
                            summary   = inp.get("summary", "Document updated.")
                            # Assign sequential indices to new_lines starting at from_i
                            indexed = [{'i': from_i + j, 'tag': ln.get('tag', 'p'), 'text': ln.get('text', '')}
                                       for j, ln in enumerate(new_lines)]
                            new_html = merge_lines_into_html(current_html, indexed)
                            # For additions/deletions that change line count, rebuild from scratch
                            if len(new_lines) != (to_i - from_i + 1):
                                orig_lines  = html_to_plain_lines(current_html)
                                before      = [l for l in orig_lines if l['i'] < from_i]
                                after_lines = [l for l in orig_lines if l['i'] > to_i]
                                # Re-index after block
                                delta = len(new_lines) - (to_i - from_i + 1)
                                for l in after_lines:
                                    l['i'] += delta
                                rebuilt = before + indexed + after_lines
                                new_html = _rebuild_html_from_lines(current_html, rebuilt)
                            restored = _persist(new_html, summary)
                            document_update = {"html": restored, "summary": summary}
                            current_html = new_html
                            tools_used.append({"name": "edit_lines", "detail": f"Lines {from_i}–{to_i}", "type": "tool"})
                            if not reply_parts:
                                reply_parts.append(summary)
                            result_summary = f"edit_lines: {summary}"

                        elif name == "update_all":
                            lines   = inp.get("lines", [])
                            summary = inp.get("summary", "Document updated.")
                            indexed = [{'i': j, 'tag': ln.get('tag', 'p'), 'text': ln.get('text', '')}
                                       for j, ln in enumerate(lines)]
                            new_html = _rebuild_html_from_lines(current_html, indexed)
                            restored = _persist(new_html, summary)
                            document_update = {"html": restored, "summary": summary}
                            current_html = new_html
                            tools_used.append({"name": "update_all", "detail": f"{len(lines)} lines", "type": "tool"})
                            if not reply_parts:
                                reply_parts.append(summary)
                            result_summary = f"update_all: {summary} ({len(lines)} lines)"

                        elif name == "add_comment":
                            new_html = _insert_comment_html(
                                current_html,
                                inp.get("comment", ""),
                                inp.get("position", "end"),
                                inp.get("after_heading", ""),
                            )
                            restored = _persist(new_html, "Comment added.")
                            document_update = {"html": restored, "summary": "Comment added."}
                            current_html = new_html
                            tools_used.append({"name": "add_comment", "detail": inp.get("position", "end"), "type": "tool"})
                            if not reply_parts:
                                reply_parts.append(document_update["summary"])
                            result_summary = "Comment added."

                        elif name == "insert_toc":
                            toc = _build_toc_html(current_html, inp.get("title", "TABLE OF CONTENTS"))
                            if toc:
                                new_html = toc + current_html
                                restored = _persist(new_html, "Table of contents inserted.")
                                document_update = {"html": restored, "summary": "Table of contents inserted."}
                                current_html = new_html
                            tools_used.append({"name": "insert_toc", "detail": "Table of contents", "type": "tool"})
                            if not reply_parts:
                                reply_parts.append(document_update["summary"] if document_update else "No headings found.")
                            result_summary = "Table of contents inserted." if document_update else "No headings found — TOC not built."

                        elif name == "renumber_sections":
                            levels = inp.get("levels", "h2_h3_h4")
                            style = inp.get("style", "number_dot")
                            renum_p = inp.get("renumber_paragraphs", True)
                            new_html = _renumber_headings(current_html, style=style, levels=levels, renumber_paragraphs=renum_p)
                            restored = _persist(new_html, f"Headings renumbered ({levels}).")
                            document_update = {"html": restored, "summary": f"Headings renumbered ({levels})."}
                            current_html = new_html
                            tools_used.append({"name": "renumber_sections", "detail": f"{levels} / {style}", "type": "tool"})
                            if not reply_parts:
                                reply_parts.append(f"All headings renumbered with multi-level numbering ({levels}).")
                            result_summary = f"Headings renumbered ({levels})."

                        elif name == "apply_formatting":
                            from_i   = int(inp.get("from_index", 0))
                            to_i     = int(inp.get("to_index", from_i))
                            fmt      = inp.get("style") or {}
                            summary  = inp.get("summary", "Formatting applied.")
                            new_html = _apply_formatting_to_html(current_html, from_i, to_i, fmt)
                            restored = _persist(new_html, summary)
                            document_update = {"html": restored, "summary": summary}
                            current_html = new_html
                            tools_used.append({"name": "apply_formatting", "detail": f"Lines {from_i}–{to_i}", "type": "tool"})
                            if not reply_parts:
                                reply_parts.append(summary)
                            result_summary = f"apply_formatting: {summary}"

                        elif name == "highlight_fields":
                            field_highlight = {
                                "field_names": inp.get("field_names", []),
                                "message":     inp.get("message", ""),
                            }
                            tools_used.append({"name": "highlight_fields", "detail": ", ".join(inp.get("field_names", [])[:3]), "type": "tool"})
                            if not reply_parts:
                                reply_parts.append(inp.get("message", "Fields highlighted."))
                            result_summary = "Fields highlighted for user attention."

                        elif name == "check_rha_compliance":
                            report = _check_rha_compliance(current_html)
                            tools_used.append({
                                "name": "check_rha_compliance",
                                "detail": f"{report['pass_count']}/{report['total_checks']} passed",
                                "type": "skill",
                            })
                            reply_parts.append(report["summary"])
                            result_summary = report["summary"]

                        elif name == "format_sa_standard":
                            add_missing = inp.get("add_missing_sections", True)
                            preserve_custom = inp.get("preserve_custom_sections", True)
                            new_html = _format_sa_standard(current_html, add_missing, preserve_custom)
                            restored = _persist(new_html, "Template restructured to standard SA lease format.")
                            document_update = {"html": restored, "summary": "Template restructured to standard SA lease format."}
                            current_html = new_html
                            tools_used.append({"name": "format_sa_standard", "detail": "13-section format", "type": "skill"})
                            if not reply_parts:
                                reply_parts.append("Template restructured to standard SA lease format.")
                            result_summary = "Template restructured to standard SA 13-section format. Missing sections added as placeholders — caller should fill them in."

                        elif name == "insert_signature_field":
                            # AI Section 3 — lift the "AI can't insert signature blocks"
                            # limitation. Append a SignatureBlock to the END of an
                            # existing line (so the user retains the surrounding
                            # paragraph text e.g. "Landlord:" before the widget).
                            after_idx = int(inp.get("after_line_index", -1))
                            field_type = inp.get("field_type", "signature")
                            signer_role = inp.get("signer_role", "landlord")
                            field_name = inp.get("field_name", "") or f"{signer_role}_{field_type}"

                            # Build the canonical signature-field HTML, then convert
                            # to a token so it travels through merge_lines_into_html
                            # like every other signature block.
                            new_tag_html = _build_signature_field_html(field_type, signer_role, field_name)
                            new_token = f"⟪SIG#{len(sig_sidecar)}⟫"
                            sig_sidecar[new_token] = new_tag_html

                            # Find the target line, append the token to its text.
                            lines = html_to_plain_lines(current_html)
                            if after_idx < 0 or after_idx >= len(lines):
                                tools_used.append({
                                    "name": "insert_signature_field",
                                    "detail": f"(invalid line index {after_idx})",
                                    "type": "warn",
                                })
                                reply_parts.append(
                                    f"I tried to insert a {field_type} field for {signer_role} "
                                    f"but the target line index {after_idx} is out of range. "
                                    f"The document has {len(lines)} lines."
                                )
                                result_summary = f"Error: line index {after_idx} out of range (document has {len(lines)} lines)."
                            else:
                                target = lines[after_idx]
                                target["text"] = (target["text"].rstrip() + " " + new_token).strip()
                                new_html = merge_lines_into_html(current_html, [target])
                                restored = _persist(new_html, f"Inserted {field_type} field for {signer_role}.")
                                document_update = {
                                    "html": restored,
                                    "summary": f"Inserted {field_type} field for {signer_role}.",
                                }
                                current_html = new_html
                                tools_used.append({
                                    "name": "insert_signature_field",
                                    "detail": f"{field_type} → {signer_role} @ line {after_idx}",
                                    "type": "tool",
                                })
                                if not reply_parts:
                                    reply_parts.append(
                                        f"Added a {field_type} field for {signer_role} at line {after_idx}."
                                    )
                                result_summary = f"Inserted {field_type} field for {signer_role} at line {after_idx}."

                        else:
                            # AI #4 fix — unknown tool fallthrough. Before this,
                            # an unrecognised tool name (e.g. Claude hallucinated
                            # "insert_signature" before the tool existed) silently
                            # completed with `reply = "Done."` and nothing changed.
                            # Surface it instead so the user sees what happened.
                            unknown_tool_attempts.append(name)
                            tools_used.append({"name": name, "detail": "(unknown tool — skipped)", "type": "warn"})
                            result_summary = f"Error: tool '{name}' is not available. Available tools: edit_lines, update_all, apply_formatting, insert_toc, renumber_sections, add_comment, highlight_fields, check_rha_compliance, format_sa_standard, insert_signature_field."

                        # AI #3: feed the tool's outcome back to Claude in the
                        # next turn so it can decide what to do next (e.g. run
                        # check_rha_compliance → see report → call format_
                        # sa_standard to fix the missing sections). Default
                        # result_summary is "OK" — most tool branches override
                        # it with a more specific outcome string above.
                        turn_tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_summary,
                        })

                # AI #3: end the multi-turn loop. Either Claude is
                # done (`end_turn`), or it didn't request any tools
                # this turn — feeding empty tool_results back would
                # just waste an API round-trip.
                if getattr(response, 'stop_reason', None) == 'end_turn' or not turn_tool_uses:
                    break
                # Continue conversation: append assistant turn + tool_result blocks.
                # Anthropic SDK accepts the response.content blocks verbatim.
                api_messages.append({"role": "assistant", "content": list(response.content)})
                api_messages.append({"role": "user", "content": turn_tool_results})

            # AI #4: if the only thing Claude did was call unknown tools,
            # tell the user — don't lie with "Done."
            if unknown_tool_attempts and not reply_parts and not document_update and not field_highlight:
                tried = ", ".join(sorted(set(unknown_tool_attempts)))
                reply_parts.append(
                    f"I tried to use a tool that doesn't exist ({tried}). "
                    "Please rephrase what you'd like me to do."
                )
            reply = " ".join(reply_parts) or "Done."

            # AI #7: preserve the conversation across doc_update turns.
            # Previously, when document_update was set, the api_history was
            # reset to a 4-message stub — meaning the next user message had
            # no memory of what was discussed about the just-edited section.
            # "Rewrite section 3" then "and add a clause about pets" was
            # broken: the second message saw only the doc state, not the
            # prior intent. Fix: keep the full conversation, just rewrite
            # the FIRST user message (the doc-context one) with the current
            # document text so Claude reads from a fresh snapshot of the doc.
            #
            # Caveat: `api_messages` after the multi-turn loop also contains
            # `tool_use`/`tool_result` blocks from any iterations. Those are
            # fine to keep in history — they're informative context for the
            # next turn ("you ran format_sa_standard and got this result").
            # The frontend stores it opaquely and sends it back on the next
            # request; we don't render them to the user.
            updated_history = [dict(m) for m in api_messages]  # shallow copy
            if document_update and updated_history:
                fresh_lines = html_to_plain_lines(current_html) if current_html else []
                fresh_doc   = plain_lines_to_text(fresh_lines) if fresh_lines else "(empty document)"
                # Replace the FIRST user message (which carried the original
                # doc context) so subsequent turns work from up-to-date HTML.
                # All later messages stay intact, including the user's
                # original request and any tool exchanges.
                for i, m in enumerate(updated_history):
                    if m.get("role") == "user":
                        updated_history[i] = {
                            "role": "user",
                            "content": f"Full document — {len(fresh_lines)} lines:\n\n{fresh_doc}",
                        }
                        break
            updated_history.append({"role": "assistant", "content": reply})

            result: dict = {"reply": reply, "api_history": updated_history}
            if document_update:
                result["document_update"] = document_update
            if field_highlight:
                result["field_highlight"] = field_highlight
            if tools_used:
                result["tools_used"] = tools_used
            return Response(result)

        except Exception as e:
            # AI #5: log via the standard logger (so Sentry / log shippers
            # pick it up) instead of `traceback.print_exc()` to stdout.
            # Without this, every chat failure in prod was invisible.
            logger.exception(
                "Lease template AI chat failed: template_id=%s user_id=%s message=%r",
                pk,
                getattr(getattr(request, "user", None), "pk", None),
                user_message[:200] if user_message else None,
            )
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExportTemplatePDFView(APIView):
    """
    GET /api/v1/leases/templates/{id}/export.pdf/

    Convert the template's content_html to a PDF and return it as a download.
    Merge field placeholders are rendered as visible blanks (e.g. ________ ).
    """
    permission_classes = [IsAgentOrAdmin]
    # Force JSON for any DRF-serialized fallback responses (e.g. 202 when
    # Gotenberg is unreachable). The success path returns an HttpResponse
    # directly with application/pdf, so this only affects fallbacks.
    renderer_classes = [JSONRenderer]

    _PDF_CSS = """
        @page {
            size: A4;
            margin: 20mm 18mm 22mm 18mm;
        }
        body {
            font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
            font-size: 10.5pt; line-height: 1.55; color: #111;
            orphans: 3; widows: 3;
            print-color-adjust: exact; -webkit-print-color-adjust: exact;
        }
        h1 { font-size: 14pt; font-weight: bold; text-align: center; margin: 14pt 0 6pt; }
        h2 { font-size: 11pt; font-weight: bold; margin: 10pt 0 3pt; border-bottom: 0.5pt solid #e5e7eb; padding-bottom: 2pt; }
        h3 { font-size: 10.5pt; font-weight: bold; margin: 7pt 0 2pt; }
        p, li { margin: 3pt 0; }
        ol, ul { margin: 3pt 0 3pt 20pt; }
        hr { border: none; border-top: 0.5pt solid #ccc; margin: 6pt 0; }
        table { border-collapse: collapse; width: 100%; margin: 4pt 0; }
        thead { display: table-header-group; }
        tr { page-break-inside: avoid; }
        td, th { border: 0.5pt solid #d1d5db; padding: 5pt 7pt; font-size: 10pt; vertical-align: top; }
        th { background: #f9fafb; font-weight: 600; }
        .merge-field { border-bottom: 1px solid #555; padding: 0 2pt; min-width: 60pt; display: inline-block; color: #333; }
        .ai-comment { background: #fffbe6; border-left: 3px solid #f59e0b; padding: 4pt 8pt; margin: 6pt 0; font-size: 9pt; color: #92400e; }
        [data-page-break] { page-break-after: always; display: block; height: 0; }
        .pdf-header { width: 100%; border-bottom: 0.5pt solid #ddd; padding-bottom: 4pt; margin-bottom: 8pt; overflow: hidden; }
        .pdf-header-left  { float: left;  font-size: 9pt; color: #666; }
        .pdf-header-right { float: right; font-size: 9pt; color: #222; font-weight: bold; }
        .pdf-footer { width: 100%; border-top: 0.5pt solid #ddd; padding-top: 4pt; margin-top: 8pt; overflow: hidden; }
        .pdf-footer-left  { float: left;  font-size: 8pt; color: #888; }
    """

    def get(self, request, pk):
        try:
            tmpl = _scoped_lease_templates(request).get(pk=pk)
        except LeaseTemplate.DoesNotExist:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        html_body = _extract_html(tmpl.content_html)
        if not html_body:
            return Response({"error": "Template has no content. Build it in the editor first."}, status=status.HTTP_400_BAD_REQUEST)

        # Render merge field spans as visible underline blanks
        html_body = re.sub(
            r'<span[^>]+data-merge-field="([^"]+)"[^>]*>.*?</span>',
            r'<span class="merge-field">&nbsp;&nbsp;{{ \1 }}&nbsp;&nbsp;</span>',
            html_body,
            flags=re.DOTALL,
        )
        # Render AI comment blocks
        html_body = re.sub(
            r'<div[^>]+data-block-comment[^>]*>(.*?)</div>',
            r'<div class="ai-comment">\1</div>',
            html_body,
            flags=re.DOTALL,
        )
        # Page break divs → CSS page breaks
        html_body = re.sub(
            r'<div[^>]+data-page-break[^>]*>.*?</div>',
            '<div data-page-break="true" style="page-break-after:always;"></div>',
            html_body, flags=re.DOTALL,
        )

        hdr_left  = tmpl.header_html or tmpl.name
        hdr_right = '<strong style="font-size:14pt;color:#1e3a5f;font-family:Georgia,serif;">k.</strong>'
        ftr_left  = tmpl.footer_html or ""

        header_div = (
            '<div class="pdf-header">'
            f'<span class="pdf-header-left">{hdr_left}</span>'
            f'<span class="pdf-header-right">{hdr_right}</span>'
            '</div>'
        )
        footer_div = (
            f'<div class="pdf-footer"><span class="pdf-footer-left">{ftr_left}</span></div>'
            if ftr_left else ''
        )

        full_html = (
            "<!DOCTYPE html><html><head>"
            f'<meta charset="UTF-8"><style>{self._PDF_CSS}</style>'
            f"</head><body>{header_div}{html_body}{footer_div}</body></html>"
        )

        from apps.esigning.gotenberg import html_to_pdf

        try:
            pdf_bytes = html_to_pdf(full_html)
        except Exception as e:
            logger.error('Gotenberg PDF generation failed for template %s: %s', pk, e)
            # Enqueue a background retry so the operator's work is not lost.
            # Force JSON rendering for the fallback response — without this DRF
            # may content-negotiate to HTML based on the Accept header set by
            # browsers, leaving callers unable to parse {queued, job_id}.
            try:
                from .models import PdfRenderJob
                from .tasks import enqueue_pdf_render
                job = PdfRenderJob.objects.create(
                    agency=tmpl.agency,
                    template=tmpl,
                    html_payload=full_html,
                    requested_by=request.user,
                )
                try:
                    enqueue_pdf_render(job.id)
                except Exception as enqueue_exc:
                    # Job row was persisted; only background dispatch failed.
                    # Still return 202 so the operator's work is queued.
                    logger.exception(
                        'Failed to dispatch PdfRenderJob %s for template %s: %s',
                        job.id, pk, enqueue_exc,
                    )
                resp = Response(
                    {
                        "queued": True,
                        "job_id": job.id,
                        "message": (
                            "Preparing your document — we'll email you when ready. "
                            "You can also check the render queue in the admin panel."
                        ),
                    },
                    status=status.HTTP_202_ACCEPTED,
                )
                resp.accepted_renderer = JSONRenderer()
                resp.accepted_media_type = "application/json"
                resp.renderer_context = {}
                return resp
            except Exception as outer_exc:
                logger.exception(
                    'Failed to enqueue PdfRenderJob for template %s: %s', pk, outer_exc
                )
            resp = Response(
                {"error": "PDF generation failed and could not be queued for retry."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
            resp.accepted_renderer = JSONRenderer()
            resp.accepted_media_type = "application/json"
            resp.renderer_context = {}
            return resp

        safe_name = re.sub(r'[^\w\s-]', '', tmpl.name).strip().replace(' ', '_') or 'template'
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{safe_name}.pdf"'
        return response


class PdfRenderJobListView(APIView):
    """
    GET  /api/v1/leases/render-jobs/          — list all jobs (admin) or own jobs (agent)
    POST /api/v1/leases/render-jobs/{id}/retry/ — manually trigger a retry
    """
    permission_classes = [IsAgentOrAdmin]

    def get(self, request):
        from .models import PdfRenderJob
        user = request.user
        # Admins see all jobs; non-admins see only their own AND only those
        # belonging to their own agency (Phase 2.4 — defence in depth).
        if user.role == User.Role.ADMIN:
            qs = PdfRenderJob.objects.select_related('template', 'requested_by').all()
        else:
            agency_id = getattr(user, "agency_id", None)
            if agency_id is None:
                qs = PdfRenderJob.objects.none()
            else:
                qs = PdfRenderJob.objects.select_related('template', 'requested_by').filter(
                    requested_by=user, agency_id=agency_id,
                )
        results = []
        for job in qs[:100]:  # cap at 100 — not paginated for now
            results.append({
                'id': job.id,
                'status': job.status,
                'attempts': job.attempts,
                'template_id': job.template_id,
                'template_name': job.template.name if job.template else None,
                'error': job.error or None,
                'result_pdf_url': (
                    request.build_absolute_uri(job.result_pdf.url)
                    if job.result_pdf
                    else None
                ),
                'created_at': job.created_at.isoformat(),
                'updated_at': job.updated_at.isoformat(),
            })
        return Response(results)


class PdfRenderJobRetryView(APIView):
    """POST /api/v1/leases/render-jobs/{id}/retry/ — re-enqueue a failed job."""
    permission_classes = [IsAgentOrAdmin]

    def post(self, request, pk):
        from .models import PdfRenderJob
        from .tasks import enqueue_pdf_render
        user = request.user
        if user.role == User.Role.ADMIN:
            qs = PdfRenderJob.objects.filter(pk=pk)
        else:
            agency_id = getattr(user, "agency_id", None)
            if agency_id is None:
                qs = PdfRenderJob.objects.none()
            else:
                qs = PdfRenderJob.objects.filter(
                    pk=pk, requested_by=user, agency_id=agency_id,
                )
        try:
            job = qs.get()
        except PdfRenderJob.DoesNotExist:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if job.status not in (PdfRenderJob.Status.FAILED, PdfRenderJob.Status.PENDING):
            return Response(
                {'error': f'Cannot retry a job with status "{job.status}".'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Reset attempt counter so the worker tries again
        job.attempts = 0
        job.status = PdfRenderJob.Status.PENDING
        job.error = ''
        job.save(update_fields=['attempts', 'status', 'error', 'updated_at'])
        enqueue_pdf_render(job.id)
        return Response({'queued': True, 'job_id': job.id})


def _sanitize_context(context: dict) -> dict:
    """Ensure all context values are strings (docxtpl requires it for text runs)."""
    safe = {}
    for key, value in context.items():
        if value is None or value == "":
            safe[key] = "—"
        elif isinstance(value, bool):
            safe[key] = "Yes" if value else "No"
        elif isinstance(value, (int, float)):
            safe[key] = str(value)
        else:
            safe[key] = str(value)
    return safe
