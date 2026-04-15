import base64
import json
import os
import re

import anthropic
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated


SYSTEM_PROMPT = """You are an expert at reading South African residential lease agreements.
Extract structured data from the lease text and return ONLY valid JSON with no extra commentary.
Do not wrap the JSON in markdown code fences.
Do not write any text before the opening { or after the closing }.
All monetary values should be plain numbers (no currency symbols or commas).
Dates must be in YYYY-MM-DD format.
If a field cannot be determined from the document, use null.
Use double quotes for all JSON keys and string values. No trailing commas."""

EXTRACTION_PROMPT = """Extract the following fields from this lease agreement and return them as JSON.

CRITICAL — READ ALL TENANTS:
South African leases frequently have 2–4 tenants who are ALL jointly and severally liable. They may appear as:
  "TENANT 1 / TENANT 2 / TENANT 3 / TENANT 4"
  "LESSEE 1 / LESSEE 2"  (Afrikaans: HUURDER)
  "THE LESSEES" followed by multiple named parties
  Listed individually under headings like "1. PARTIES" or "DIE HUURDER"
  Repeated in a signature block at the back of the document
  Klikk lease template: "1.2.1 Tenant One", "1.2.2 Tenant Two (if applicable)",
    "1.2.3 Tenant Three (if applicable)", "1.2.4 Tenant Four (if applicable)" — each
    in their own table block with "Tenant/Occupant 1/2/3/4 Full Legal Name:" field.

YOU MUST scan the ENTIRE document — intro, body, annexures, AND signature pages — and capture EVERY person who appears as a lessee/tenant/huurder.
Do NOT stop after finding the first name. Put the first one in primary_tenant and ALL remaining ones in co_tenants.

IMPORTANT DISTINCTIONS:
- "tenants" = legal signatories (jointly and severally liable). There can be up to 4. ALL are equally important.
- "occupants" = people who physically live in the property (may overlap with tenants, or be different — e.g. a student whose parent signs).
- "guarantors" = sureties who guarantee a specific tenant's obligations.
- "Guardian/Co-Debtor" rows (e.g. "Tenant 1 Guardian/Co-Debtor Full Legal Name (If Applicable)")
  are GUARANTORS, NOT additional tenants. Map them to the guarantors array with for_tenant set
  to the tenant they cover. Do NOT place guardians/co-debtors in co_tenants.

PROPERTY / PREMISES (critical — SA leases use many wordings):
- Look for "PREMISES", "DIE PAND", "ERF", "UNIT", "SECTIONAL TITLE", "ADDRESS",
  "PROPERTY", "STAND", "BOSCH EN DAL", farm/estate names, unit numbers in headers.
- Always fill property_address with the full human-readable location (street + suburb + town + province + postal if visible).
- Also set property_name to a short label (e.g. estate + unit, or first line of address).
- If city / province / postal appear separately, set property_city, property_province, property_postal_code.

Return this exact JSON structure:

{
  "primary_tenant": {
    "full_name": "First tenant full name — the one listed first as TENANT 1 or HUURDER 1",
    "id_number": "SA ID or passport number",
    "phone": "Phone number",
    "email": "Email address"
  },
  "co_tenants": [
    {
      "full_name": "EVERY additional tenant — TENANT 2, TENANT 3, TENANT 4 etc.",
      "id_number": "ID number",
      "phone": "Phone",
      "email": "Email"
    }
  ],
  "occupants": [
    {
      "full_name": "Occupant full name",
      "id_number": "ID number",
      "phone": "Phone",
      "email": "Email",
      "relationship_to_tenant": "e.g. self, spouse, child, employee, student"
    }
  ],
  "guarantors": [
    {
      "for_tenant": "Full name of the tenant this guarantor covers",
      "full_name": "Guarantor/surety full name",
      "id_number": "Guarantor ID",
      "phone": "Guarantor phone",
      "email": "Guarantor email"
    }
  ],
  "monthly_rent": 5000,
  "deposit": 5000,
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "max_occupants": 1,
  "water_included": true,
  "water_limit_litres": 4000,
  "electricity_prepaid": true,
  "notice_period_days": 20,
  "early_termination_penalty_months": 3,
  "payment_reference": "e.g. '18 Irene - Smith'",
  "property_name": "Short name e.g. Bosch En Dal Unit 1 or building name",
  "property_address": "Full address line as on lease",
  "property_city": "City or town",
  "property_province": "Province e.g. Western Cape",
  "property_postal_code": "Postal code",
  "unit_number": "Unit/flat/erf stand number if present"
}

If a field is not found, use null. Arrays may be empty [].

Lease document text:
"""


def _message_text(message) -> str:
    parts: list[str] = []
    for block in message.content:
        if getattr(block, "type", None) == "text" and hasattr(block, "text"):
            parts.append(block.text)
    return "".join(parts).strip()


def _strip_markdown_fence(text: str) -> str:
    text = text.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return text


def _extract_json_object(s: str) -> str | None:
    """Find first top-level {...} with string-aware brace matching."""
    s = s.strip()
    start = s.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(s)):
        ch = s[i]
        if escape:
            escape = False
            continue
        if in_string:
            if ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1]
    return None


def _relax_json(s: str) -> str:
    """Remove trailing commas before } or ] (common LLM mistake)."""
    return re.sub(r",(\s*[\]}])", r"\1", s)


def _parse_extracted_json(raw: str) -> dict | None:
    cleaned = _strip_markdown_fence(raw)
    candidate = _extract_json_object(cleaned)
    if candidate is None:
        candidate = cleaned.strip()
    for blob in (candidate, _relax_json(candidate)):
        try:
            out = json.loads(blob)
            return out if isinstance(out, dict) else None
        except json.JSONDecodeError:
            continue
    return None


def _repair_json_with_claude(client: anthropic.Anthropic, broken: str) -> dict | None:
    snippet = broken.strip()
    if len(snippet) > 100_000:
        snippet = snippet[:100_000]
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            system="Output only valid JSON. No markdown fences, no explanation, no keys but the JSON object.",
            messages=[
                {
                    "role": "user",
                    "content": (
                        "The text below was meant to be a single JSON object from a lease extractor "
                        "but it is invalid (truncated, extra prose, bad commas, or markdown). "
                        "Return ONE valid JSON object only. Preserve all fields you can read. "
                        "If JSON was cut off mid-string, fix or null that field. "
                        "Use null for unknown scalars and [] for unknown arrays.\n\n---\n" + snippet
                    ),
                }
            ],
        )
    except Exception:
        return None
    return _parse_extracted_json(_message_text(message))


# Always send the native PDF to Claude — pypdf text extraction is unreliable for table-structured leases.


def normalize_extracted_lease(d: dict) -> dict:
    """Flatten nested `property` and alternate keys so the admin UI receives top-level fields."""
    if not isinstance(d, dict):
        return d
    out = dict(d)

    nested = out.get("property")
    if isinstance(nested, dict):
        addr = (nested.get("address") or nested.get("full_address") or nested.get("street") or "").strip()
        name = (nested.get("name") or nested.get("label") or "").strip()
        city = (nested.get("city") or nested.get("town") or "").strip()
        prov = (nested.get("province") or "").strip()
        pc = nested.get("postal_code") or nested.get("postal") or nested.get("postcode")
        if addr and not out.get("property_address"):
            out["property_address"] = addr
        if name and not out.get("property_name"):
            out["property_name"] = name
        if city and not out.get("property_city"):
            out["property_city"] = city
        if prov and not out.get("property_province"):
            out["property_province"] = prov
        if pc and not out.get("property_postal_code"):
            out["property_postal_code"] = str(pc).strip()

    for alt_key in (
        "premises_address",
        "leased_premises",
        "premises",
        "dwelling_address",
        "address_of_premises",
        "property_full_address",
        "full_address",
        "address",
    ):
        v = out.get(alt_key)
        if isinstance(v, str) and v.strip() and not out.get("property_address"):
            out["property_address"] = v.strip()

    if isinstance(out.get("property_name"), str) and out["property_name"].strip():
        pass  # keep
    elif out.get("property_address"):
        first = str(out["property_address"]).split(",")[0].strip()
        if first:
            out["property_name"] = first

    return out


class ParseLeaseDocumentView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"error": "No file provided."}, status=400)

        if not file.name.lower().endswith(".pdf"):
            return Response({"error": "Only PDF files are supported."}, status=400)

        pdf_bytes = b"".join(file.chunks())
        if len(pdf_bytes) > 32 * 1024 * 1024:
            return Response({"error": "PDF is too large (max 32 MB)."}, status=400)

        # Read key directly from .env file (bypass os.environ which Claude Code clears)
        _env_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", ".env")
        )
        api_key = ""
        try:
            with open(_env_path) as _f:
                for _line in _f:
                    _line = _line.strip()
                    if _line.startswith("ANTHROPIC_API_KEY="):
                        api_key = _line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
        except FileNotFoundError:
            pass
        if not api_key:
            return Response({"error": "ANTHROPIC_API_KEY is not configured on the server."}, status=500)

        client = anthropic.Anthropic(api_key=api_key)

        b64_pdf = base64.standard_b64encode(pdf_bytes).decode("ascii")
        user_content = [
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": b64_pdf,
                },
            },
            {
                "type": "text",
                "text": (
                    EXTRACTION_PROMPT
                    + "\n\nThe lease is attached as a PDF. Read the full document visually, "
                    "including all tables and form fields."
                ),
            },
        ]

        try:
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8192,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
            )
        except Exception as e:
            return Response({"error": f"Claude API error: {e}"}, status=502)

        raw = _message_text(message)

        extracted = _parse_extracted_json(raw)
        if extracted is None:
            extracted = _repair_json_with_claude(client, raw)

        if extracted is None:
            return Response(
                {
                    "error": "Claude returned invalid JSON. Try a shorter PDF or re-upload.",
                    "raw": raw[:8000] + ("…" if len(raw) > 8000 else ""),
                },
                status=502,
            )

        extracted = normalize_extracted_lease(extracted)
        extracted["_parse_via"] = "pdf_document"

        return Response(extracted)
