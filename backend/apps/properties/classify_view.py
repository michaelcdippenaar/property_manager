"""
AI document classifier agent for owner/landlord onboarding.

POST /api/v1/properties/landlords/{id}/classify/

Reads all LandlordDocuments uploaded for this landlord, sends them to
Claude (claude-sonnet-4-6 with vision), and returns a fully structured
owner_classification.json — also auto-populating the Landlord record with
extracted fields (name, registration_number, email, vat_number, etc.).
"""

import base64
import json
import mimetypes
from datetime import date

import anthropic
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status as http_status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import IsAgentOrAdmin
from .models import Landlord, LandlordDocument

# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert South African property compliance agent specialising in FICA and CIPC/CIPRO documentation. Your job is to read owner/landlord documents and produce a structured classification JSON.

## Document buckets

**FICA** — KYC documents required before financial onboarding:
- SA Identity Document — Smart ID card or green ID book (`type: "sa_id"`)
- Passport — any nationality; for foreign nationals or when SA ID is not available (`type: "passport"`)
- Driver's Licence — SA-issued (`type: "drivers_licence"`) — accepted as secondary photo ID, NOT a substitute for primary ID
- Proof of Address / Proof of Residence (utility bill, municipal account, bank statement showing address — must be <3 months old) (`type: "proof_of_address"`)
- Bank Confirmation Letter (on bank letterhead) (`type: "bank_confirmation"`)
- SARS Tax Number / Tax Clearance Certificate (`type: "tax_certificate"`)
- VAT Registration Certificate (`type: "vat_certificate"`)

For every identity document (SA ID, passport, driver's licence), extract into `extracted`:
- `id_number` (13 digits for SA ID) or `passport_number`
- `full_name`, `surname`, `given_names`
- `date_of_birth` (ISO YYYY-MM-DD)
- `nationality` (passport only)
- `expiry_date` (passport / licence only — ISO)
- `gender` if printed
Associate the person to the right entity via `persons_graph` (e.g. a director's passport links back to the company via their `roles`).

**CIPC/CIPRO** — Entity registration and governance:
- CoR14.3 — Registration Certificate (Company name, reg number YYYY/XXXXXX/07)
- CoR15.1A / CoR15.1B — Memorandum of Incorporation (MOI)
- CoR39 — Director Notice (lists directors with ID numbers)
- CoR21 — Registered Office Notice
- CoR123 — Annual Return
- CoR40 — Winding-up / Liquidation Notice
- CK1 — CC Founding Statement (member percentages, CK number)
- CK2 / CK2A — CC Amendment
- Letters of Authority (Master of the High Court) — Trust
- Trust Deed / Deed of Trust
- Partnership Agreement

## Registration number formats
- YYYY/XXXXXX/07 = Pty Ltd
- YYYY/XXXXXX/06 = (Ltd)
- YYYY/XXXXXX/08 = CC
- YYYY/XXXXXX/21 = NPC
- CKxxxx/yy = old-format CC
- ITxxxx/yyyy = Trust

## Red flags to check
- Company CIPC status listed as "Deregistered"
- Proof of address older than 3 months from today ({today})
- Director on CoR39 has no ID document in the set
- Trust deed present but no Letter of Authority
- Company registered >1 year ago but no annual return (CoR123) found
- Company owned by trust but no trust documents present

## Output schema (respond ONLY with valid JSON — no markdown, no explanation)

{{
  "entity_type": "Individual | Company | Trust | CC | Partnership",
  "entity_subtype": "Pty Ltd | NPC | SOC Ltd | Ltd | null",
  "owned_by_trust": false,
  "trust_entity": null,
  "fica": {{
    "status": "complete | incomplete | needs_review",
    "documents": [
      {{
        "type": "document type label",
        "filename": "original filename",
        "extracted": {{}},
        "status": "found"
      }}
    ],
    "missing": ["list of missing required document types"],
    "flags": ["list of warning strings"]
  }},
  "cipc": {{
    "status": "complete | incomplete | needs_review",
    "documents": [
      {{
        "type": "CoR14.3 | CoR39 | CK1 | etc",
        "filename": "original filename",
        "extracted": {{}},
        "status": "found"
      }}
    ],
    "missing": ["list of missing required document types"],
    "flags": ["list of warning strings"]
  }},
  "extracted_data": {{
    "registration_number": "",
    "company_name": "",
    "directors": [],
    "address": "",
    "tax_number": "",
    "vat_number": "",
    "representative_name": "",
    "representative_id_number": "",
    "email": "",
    "phone": ""
  }},
  "persons_graph": [],
  "classified_at": "ISO8601 timestamp"
}}

For `trust_entity` when `owned_by_trust` is true:
{{
  "trust_name": "",
  "trust_number": "",
  "urn": "",
  "trustees": [{{"full_name": "", "id_number": ""}}],
  "fica": {{"status": "...", "documents": [], "missing": [], "flags": []}},
  "cipc": {{"status": "...", "documents": [], "missing": [], "flags": []}}
}}

For each person in `persons_graph`:
{{
  "id_number": "13 digits",
  "full_name": "FULL NAME",
  "roles": [{{"entity": "entity name", "entity_type": "Company|Trust|CC", "role": "Director|Trustee|Member|etc"}}],
  "fica_documents_found": ["SA ID (filename.pdf)"],
  "fica_reuse_note": null,
  "joint_flag": false,
  "joint_description": null,
  "system_records": [],
  "system_note": null
}}

Extract only what is explicitly present in the documents. Do not guess or infer values not found in the documents."""


def _encode_file(doc: LandlordDocument = None, *, file_field=None, filename: str = "") -> dict | None:
    """
    Return an Anthropic content block for a document file.

    Can accept either:
      - a LandlordDocument instance (doc)
      - a raw Django FieldFile + filename (for registration_document)
    """
    try:
        if doc is not None:
            fname = doc.filename
            fobj = doc.file
        elif file_field:
            fname = filename or file_field.name
            fobj = file_field
        else:
            return None

        mime, _ = mimetypes.guess_type(fname)
        if not mime:
            mime = "application/octet-stream"

        with fobj.open("rb") as f:
            data = f.read()

        # Images — pass as vision blocks
        if mime.startswith("image/"):
            return {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": mime,
                    "data": base64.standard_b64encode(data).decode(),
                },
            }

        # PDFs — pass as document blocks (supported by claude-sonnet-4-6)
        if mime == "application/pdf":
            return {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": base64.standard_b64encode(data).decode(),
                },
            }

        # Plain text / other — truncate and send as text
        try:
            text = data.decode("utf-8", errors="replace")[:8000]
        except Exception:
            return None
        return {"type": "text", "text": f"[File: {fname}]\n{text}"}

    except Exception:
        return None


class LandlordClassifyView(APIView):
    """
    POST /api/v1/properties/landlords/{pk}/classify/

    Runs the AI document classifier on all uploaded LandlordDocuments.
    Returns the classification JSON and patches the Landlord record.
    """
    permission_classes = [IsAuthenticated, IsAgentOrAdmin]

    def post(self, request, pk=None):
        try:
            landlord = Landlord.objects.get(pk=pk)
        except Landlord.DoesNotExist:
            return Response({"detail": "Landlord not found."}, status=http_status.HTTP_404_NOT_FOUND)

        docs = list(landlord.documents.all())
        has_reg_doc = bool(landlord.registration_document)
        if not docs and not has_reg_doc:
            return Response(
                {"detail": "No documents uploaded. Upload documents first."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        total = len(docs) + (1 if has_reg_doc else 0)

        # Build message content: label + file block per document
        content = [
            {
                "type": "text",
                "text": (
                    f"Classify and extract data from the following {total} owner documents "
                    f"for entity: {landlord.name or 'Unknown'} (current type: {landlord.landlord_type}).\n\n"
                    "Return ONLY the JSON object as specified in your instructions."
                ),
            }
        ]

        skipped = []

        # Include the registration document if present
        if has_reg_doc:
            reg_name = landlord.registration_document_name or landlord.registration_document.name
            block = _encode_file(file_field=landlord.registration_document, filename=reg_name)
            if block:
                content.append({"type": "text", "text": f"\n--- Document: {reg_name} (Registration Document) ---"})
                content.append(block)
            else:
                skipped.append(reg_name)

        for doc in docs:
            block = _encode_file(doc)
            if block:
                content.append({"type": "text", "text": f"\n--- Document: {doc.filename} ---"})
                content.append(block)
            else:
                skipped.append(doc.filename)

        if len(content) == 1:
            return Response(
                {"detail": "No readable documents found (unsupported formats?)."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        api_key = getattr(settings, "ANTHROPIC_API_KEY", "") or ""
        if not api_key:
            return Response(
                {"detail": "ANTHROPIC_API_KEY not configured."},
                status=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        client = anthropic.Anthropic(api_key=api_key)
        system = SYSTEM_PROMPT.format(today=date.today().isoformat())

        try:
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=system,
                messages=[{"role": "user", "content": content}],
            )
        except anthropic.APIError as exc:
            return Response(
                {"detail": f"Claude API error: {exc}"},
                status=http_status.HTTP_502_BAD_GATEWAY,
            )

        raw = message.content[0].text.strip()

        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.rsplit("```", 1)[0].strip()

        try:
            classification = json.loads(raw)
        except json.JSONDecodeError:
            return Response(
                {"detail": "Claude returned invalid JSON.", "raw": raw},
                status=http_status.HTTP_502_BAD_GATEWAY,
            )

        # ── Auto-patch landlord fields from extracted_data ─────────────────
        extracted = classification.get("extracted_data", {})
        patch_fields = []

        def _set(field, value):
            if value and not getattr(landlord, field, None):
                setattr(landlord, field, value)
                patch_fields.append(field)

        _set("name", extracted.get("company_name") or extracted.get("full_name"))
        _set("registration_number", extracted.get("registration_number"))
        _set("vat_number", extracted.get("vat_number"))
        _set("email", extracted.get("email"))
        _set("phone", extracted.get("phone"))
        _set("representative_name", extracted.get("representative_name"))
        _set("representative_id_number", extracted.get("representative_id_number"))

        # Entity type mapping
        entity_type_map = {
            "Company": "company",
            "Trust": "trust",
            "Individual": "individual",
            "CC": "cc",
            "Close Corporation": "cc",
            "Partnership": "partnership",
        }
        new_type = entity_type_map.get(classification.get("entity_type", ""), "")
        if new_type and landlord.landlord_type == "individual":
            landlord.landlord_type = new_type
            patch_fields.append("landlord_type")

        if classification.get("owned_by_trust") and not landlord.owned_by_trust:
            landlord.owned_by_trust = True
            patch_fields.append("owned_by_trust")

        # Address from extracted
        addr_str = extracted.get("address", "")
        if addr_str and not landlord.address.get("street"):
            landlord.address = {"street": addr_str}
            patch_fields.append("address")

        # Always save classification data
        landlord.classification_data = classification
        patch_fields.append("classification_data")

        if patch_fields:
            landlord.save(update_fields=patch_fields)

        return Response({
            "classification": classification,
            "patched_fields": patch_fields,
            "skipped_files": skipped,
        })


# ── Shared helpers ────────────────────────────────────────────────────────────

def _call_claude(content: list, api_key: str) -> tuple[dict | None, str | None]:
    """Send content blocks to Claude and return (parsed_json, error_string)."""
    client = anthropic.Anthropic(api_key=api_key)
    system = SYSTEM_PROMPT.format(today=date.today().isoformat())

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": content}],
        )
    except anthropic.APIError as exc:
        return None, f"Claude API error: {exc}"

    raw = message.content[0].text.strip()

    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rsplit("```", 1)[0].strip()

    try:
        return json.loads(raw), None
    except json.JSONDecodeError:
        return None, f"Claude returned invalid JSON: {raw[:300]}"


def _patch_landlord(landlord: Landlord, classification: dict) -> list[str]:
    """Apply extracted_data from classification to landlord fields. Returns list of patched field names."""
    extracted = classification.get("extracted_data", {})
    patch_fields = []

    def _set(field, value):
        if value and not getattr(landlord, field, None):
            setattr(landlord, field, value)
            patch_fields.append(field)

    _set("name", extracted.get("company_name") or extracted.get("full_name"))
    _set("registration_number", extracted.get("registration_number"))
    _set("vat_number", extracted.get("vat_number"))
    _set("email", extracted.get("email"))
    _set("phone", extracted.get("phone"))
    _set("representative_name", extracted.get("representative_name"))
    _set("representative_id_number", extracted.get("representative_id_number"))

    entity_type_map = {
        "Company": "company", "Trust": "trust", "Individual": "individual",
        "CC": "cc", "Close Corporation": "cc", "Partnership": "partnership",
    }
    new_type = entity_type_map.get(classification.get("entity_type", ""), "")
    if new_type and landlord.landlord_type == "individual":
        landlord.landlord_type = new_type
        patch_fields.append("landlord_type")

    if classification.get("owned_by_trust") and not landlord.owned_by_trust:
        landlord.owned_by_trust = True
        patch_fields.append("owned_by_trust")

    addr_str = extracted.get("address", "")
    if addr_str and not landlord.address.get("street"):
        landlord.address = {"street": addr_str}
        patch_fields.append("address")

    landlord.classification_data = classification
    patch_fields.append("classification_data")

    if patch_fields:
        landlord.save(update_fields=patch_fields)

    return patch_fields


class LandlordClassifyRegistrationView(APIView):
    """
    POST /api/v1/properties/landlords/{pk}/classify-registration/

    Classifies ONLY the single registration document (CIPC cert, trust deed, ID).
    Extracts entity type, registration number, directors, etc. and auto-fills
    the Landlord record.
    """
    permission_classes = [IsAuthenticated, IsAgentOrAdmin]

    def post(self, request, pk=None):
        try:
            landlord = Landlord.objects.get(pk=pk)
        except Landlord.DoesNotExist:
            return Response({"detail": "Landlord not found."}, status=http_status.HTTP_404_NOT_FOUND)

        if not landlord.registration_document:
            return Response(
                {"detail": "No registration document uploaded."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        api_key = getattr(settings, "ANTHROPIC_API_KEY", "") or ""
        if not api_key:
            return Response(
                {"detail": "ANTHROPIC_API_KEY not configured."},
                status=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        reg_name = landlord.registration_document_name or landlord.registration_document.name
        block = _encode_file(file_field=landlord.registration_document, filename=reg_name)
        if not block:
            return Response(
                {"detail": f"Cannot read file: {reg_name}"},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        content = [
            {
                "type": "text",
                "text": (
                    f"Classify and extract data from this single registration document "
                    f"for entity: {landlord.name or 'Unknown'} (current type: {landlord.landlord_type}).\n"
                    f"Document filename: {reg_name}\n\n"
                    "Return ONLY the JSON object as specified in your instructions. "
                    "Since this is only a single registration document, mark any FICA/CIPC items "
                    "not present in this document as missing — do not guess."
                ),
            },
            {"type": "text", "text": f"\n--- Document: {reg_name} ---"},
            block,
        ]

        classification, error = _call_claude(content, api_key)
        if error:
            return Response({"detail": error}, status=http_status.HTTP_502_BAD_GATEWAY)

        patch_fields = _patch_landlord(landlord, classification)

        return Response({
            "classification": classification,
            "patched_fields": patch_fields,
            "document": reg_name,
        })
