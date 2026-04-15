"""
Parse an existing (often pre-signed) rental mandate PDF and extract
structured fields so the admin Create/Edit Mandate modal can be pre-filled.

Mirrors backend/apps/leases/parse_view.py (the contract/lease extractor)
and backend/apps/properties/classify_view.py (for the Anthropic client
bootstrap convention). No database writes — this endpoint is read-only
from the server's perspective; the admin re-posts the confirmed values
to the existing /properties/mandates/ endpoint to actually create the
RentalMandate.
"""

import base64
import json
import os
import re

import anthropic
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


SYSTEM_PROMPT = """You are an expert at reading South African residential rental-management mandates.
Extract structured data from the mandate and return ONLY valid JSON with no extra commentary.
Do not wrap the JSON in markdown code fences.
Do not write any text before the opening { or after the closing }.
All monetary values must be plain numbers (no currency symbols, no commas).
Dates must be in YYYY-MM-DD format.
If a field cannot be determined from the document, use null.
Never invent values — only return what is explicitly present on the page.
Use double quotes for all JSON keys and string values. No trailing commas."""


EXTRACTION_PROMPT = """Extract the fields below from this rental management mandate and return them as JSON.

A rental mandate is a contract between a PROPERTY OWNER (the landlord) and a MANAGING AGENT /
LETTING AGENT / ESTATE AGENCY that authorises the agent to find tenants, manage the property,
and/or collect rent on the owner's behalf. In South Africa these are typically titled:
  "Mandate Agreement", "Rental Management Mandate", "Sole Mandate", "Letting Mandate",
  "Mandate to Let", "Full Management Mandate", "Opdrag tot Verhuring" (Afrikaans).

MANDATE TYPE — normalise to ONE of these four values based on the scope described:
  - "full_management"  : agent handles letting, rent collection, maintenance & admin (typically 8–12% monthly)
  - "rent_collection"  : agent collects rent and disburses to owner; owner handles the rest (typically 4–6% monthly)
  - "letting_only"     : agent finds a tenant only; owner manages thereafter (typically 1 month placement fee)
  - "finders_fee"      : once-off finder's fee for sourcing a tenant, no ongoing management

EXCLUSIVITY — look for wording like "sole mandate", "sole and exclusive", "open mandate",
  "non-exclusive", "multi-listing". Normalise to "sole" or "open".

COMMISSION — two linked fields:
  - commission_rate: the number (e.g. 10 for "10%", or 1 for "1 month's rent")
  - commission_period: "monthly" if the commission recurs each month the tenant pays rent,
                       "once_off" if it's a single placement / finder fee

DATES — start_date is the mandate commencement. end_date is the expiry/termination date if
  fixed; null if the mandate is open-ended or auto-renewing.

NOTICE PERIOD — days of written notice either party must give to terminate. Common values
  are 30, 60, 90 days. Extract as an integer.

MAINTENANCE THRESHOLD — only relevant for full_management. The Rand amount per incident
  the agent may spend without calling the owner first. E.g. "R2,000 per incident" → 2000.

OWNER / AGENT DETAILS — useful so the reviewer can cross-check against the landlord record
  in Klikk. Extract as plain strings; omit if not shown.

Return this exact JSON structure:

{
  "mandate_type": "full_management" | "letting_only" | "rent_collection" | "finders_fee" | null,
  "exclusivity": "sole" | "open" | null,
  "commission_rate": 10,
  "commission_period": "monthly" | "once_off" | null,
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "notice_period_days": 60,
  "maintenance_threshold": 2000,
  "owner_name": "Full name (or entity name) of the owner / landlord / lessor",
  "owner_email": "Owner email if present",
  "owner_id_or_reg": "Owner SA ID or company reg number",
  "agent_name": "Named individual agent signing on behalf of the agency",
  "agent_company": "Agency / estate agent company name",
  "agent_fidelity_fund_number": "EAAB FFC or BRN if printed on the mandate",
  "property_address": "Full address of the property being mandated",
  "notes": "Any material clauses not captured above (e.g. bespoke marketing budget, exclusion lists)",
  "is_signed": true,
  "signature_observations": "Brief note on what signatures are visible — e.g. 'Owner wet-signed 2024-03-15; agent countersigned 2024-03-16'"
}

If a field is not found, use null. Do NOT guess. If this document is clearly NOT a rental
management mandate (e.g. a lease between landlord and tenant, a sale agreement, a POA, an
FICA form), return:

{ "error": "not_a_mandate", "document_appears_to_be": "short description" }

Mandate document is attached as a PDF. Read the full document, including signature pages.
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
    return re.sub(r",(\s*[\]}])", r"\1", s)


def _parse_json(raw: str) -> dict | None:
    cleaned = _strip_markdown_fence(raw)
    candidate = _extract_json_object(cleaned) or cleaned.strip()
    for blob in (candidate, _relax_json(candidate)):
        try:
            out = json.loads(blob)
            return out if isinstance(out, dict) else None
        except json.JSONDecodeError:
            continue
    return None


def _load_api_key() -> str:
    """Read ANTHROPIC_API_KEY from .env (bypass os.environ which Claude Code clears)."""
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key
    env_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    )
    try:
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("ANTHROPIC_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return ""


def _normalise_extracted(d: dict) -> dict:
    """Coerce values into the shapes the admin modal expects."""
    out = dict(d)

    # mandate_type — lowercase + trim; map a few common freeform phrasings
    mt = (out.get("mandate_type") or "").strip().lower().replace(" ", "_").replace("-", "_")
    mt_aliases = {
        "full": "full_management",
        "management": "full_management",
        "full_mandate": "full_management",
        "letting": "letting_only",
        "placement": "letting_only",
        "rent_collection_only": "rent_collection",
        "collection": "rent_collection",
        "finder": "finders_fee",
        "finders": "finders_fee",
        "finder_fee": "finders_fee",
        "finders_fee_only": "finders_fee",
    }
    mt = mt_aliases.get(mt, mt)
    if mt not in {"full_management", "letting_only", "rent_collection", "finders_fee"}:
        mt = None
    out["mandate_type"] = mt

    ex = (out.get("exclusivity") or "").strip().lower()
    if "sole" in ex or "exclusive" in ex:
        ex = "sole"
    elif "open" in ex or "non" in ex:
        ex = "open"
    else:
        ex = None
    out["exclusivity"] = ex

    cp = (out.get("commission_period") or "").strip().lower().replace(" ", "_").replace("-", "_")
    if cp in {"once", "onceoff", "once_off", "one_off", "oneoff"}:
        cp = "once_off"
    elif cp in {"monthly", "month", "per_month", "recurring"}:
        cp = "monthly"
    else:
        cp = None
    out["commission_period"] = cp

    for num_field in ("commission_rate", "maintenance_threshold"):
        v = out.get(num_field)
        if isinstance(v, str):
            cleaned = re.sub(r"[^\d.]", "", v)
            try:
                out[num_field] = float(cleaned) if cleaned else None
            except ValueError:
                out[num_field] = None

    npd = out.get("notice_period_days")
    if isinstance(npd, str):
        m = re.search(r"\d+", npd)
        out["notice_period_days"] = int(m.group(0)) if m else None

    return out


def _compute_missing(extracted: dict) -> list[str]:
    required = [
        "mandate_type",
        "commission_rate",
        "commission_period",
        "start_date",
    ]
    return [f for f in required if not extracted.get(f)]


class ParseMandateDocumentView(APIView):
    """
    POST /api/v1/properties/<property_id>/mandates/parse-document/
    multipart/form-data: { document: <file> }

    Returns:
      200 { extracted: {...}, missing: [...], warnings: [...], raw_meta: {...} }
      400 bad input (no file, wrong type, too large)
      422 document is not a mandate
      502 Claude error / unparseable JSON
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request, property_id: int):
        f = request.FILES.get("document") or request.FILES.get("file")
        if not f:
            return Response({"error": "No file provided. Use field name 'document'."}, status=400)

        filename = f.name or ""
        lower = filename.lower()
        if not lower.endswith(".pdf"):
            return Response(
                {"error": "Only PDF mandates are supported. Export to PDF first."},
                status=400,
            )

        pdf_bytes = b"".join(f.chunks())
        if len(pdf_bytes) > 32 * 1024 * 1024:
            return Response({"error": "PDF is too large (max 32 MB)."}, status=400)

        api_key = _load_api_key()
        if not api_key:
            return Response(
                {"error": "ANTHROPIC_API_KEY is not configured on the server."},
                status=500,
            )

        client = anthropic.Anthropic(api_key=api_key)

        b64 = base64.standard_b64encode(pdf_bytes).decode("ascii")
        user_content = [
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": b64,
                },
            },
            {"type": "text", "text": EXTRACTION_PROMPT},
        ]

        try:
            message = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
            )
        except Exception as e:
            return Response({"error": f"Claude API error: {e}"}, status=502)

        raw = _message_text(message)
        parsed = _parse_json(raw)
        if parsed is None:
            return Response(
                {
                    "error": "Could not parse Claude's response as JSON.",
                    "raw_excerpt": raw[:2000],
                },
                status=502,
            )

        # Negative case — Claude says it's not a mandate.
        if parsed.get("error") == "not_a_mandate":
            return Response(
                {
                    "error": "Could not identify mandate fields in this document.",
                    "document_appears_to_be": parsed.get("document_appears_to_be"),
                },
                status=422,
            )

        extracted = _normalise_extracted(parsed)
        missing = _compute_missing(extracted)

        return Response(
            {
                "extracted": extracted,
                "missing": missing,
                "warnings": [],
                "property_id": property_id,
                "filename": filename,
            }
        )
