import json
import os
import tempfile

import anthropic
from pypdf import PdfReader
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated


SYSTEM_PROMPT = """You are an expert at reading South African residential lease agreements.
Extract structured data from the lease text and return ONLY valid JSON with no extra commentary.
All monetary values should be plain numbers (no currency symbols or commas).
Dates must be in YYYY-MM-DD format.
If a field cannot be determined from the document, use null."""

EXTRACTION_PROMPT = """Extract the following fields from this lease agreement and return them as JSON.

IMPORTANT DISTINCTIONS:
- "tenants" = legal signatories who are jointly and severally liable (financially responsible). There can be up to 4.
- "occupants" = people who physically live in the property. This may overlap with tenants or be entirely different people (e.g. a student whose parent signs, or an employee whose company signs).
- "guardians" = sureties/guarantors who guarantee a specific tenant's obligations.

Return this exact JSON structure:

{
  "primary_tenant": {
    "full_name": "Primary/first tenant full name",
    "id_number": "SA ID or passport number",
    "phone": "Phone number",
    "email": "Email address"
  },
  "co_tenants": [
    {
      "full_name": "Co-tenant full name",
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
  "guardians": [
    {
      "for_tenant": "Full name of the tenant this guardian covers",
      "full_name": "Guardian/surety full name",
      "id_number": "Guardian ID",
      "phone": "Guardian phone",
      "email": "Guardian email"
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
  "property_address": "Full property address",
  "unit_number": "Unit/flat number if present"
}

If a field is not found, use null. Arrays may be empty [].

Lease document text:
"""


class ParseLeaseDocumentView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"error": "No file provided."}, status=400)

        if not file.name.lower().endswith(".pdf"):
            return Response({"error": "Only PDF files are supported."}, status=400)

        # Extract text from PDF
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                for chunk in file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name

            reader = PdfReader(tmp_path)
            pages_text = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text)
            pdf_text = "\n\n".join(pages_text)
        finally:
            os.unlink(tmp_path)

        if not pdf_text.strip():
            return Response({"error": "Could not extract text from PDF. It may be scanned/image-based."}, status=400)

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

        # Truncate to ~80k chars to stay within context limits
        truncated_text = pdf_text[:80000]

        try:
            message = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": EXTRACTION_PROMPT + truncated_text,
                    }
                ],
            )
        except Exception as e:
            return Response({"error": f"Claude API error: {e}"}, status=502)

        raw = message.content[0].text.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        try:
            extracted = json.loads(raw)
        except json.JSONDecodeError:
            return Response({"error": "Claude returned invalid JSON.", "raw": raw}, status=502)

        return Response(extracted)
