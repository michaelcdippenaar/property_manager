"""
AI municipal bill parser for property onboarding.

POST /api/v1/properties/parse-municipal-bill/

Accepts a municipal bill upload (PDF/image), sends it to Claude,
and returns structured property data extracted from the bill.
"""

import base64
import json
import mimetypes
from datetime import date

import anthropic
from django.conf import settings
from rest_framework import parsers, status as http_status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAgentOrAdmin

SYSTEM_PROMPT = """You are an expert at reading South African municipal bills / rates accounts.

Given a municipal bill document (PDF or image), extract all property and account information you can find.

Common South African municipalities: City of Cape Town, Stellenbosch, Drakenstein, City of Johannesburg, eThekwini, Tshwane, Nelson Mandela Bay, Buffalo City, Mangaung, etc.

## Fields to extract

- **property_name**: The property/stand name or description (e.g. "18 Irene Park", "Erf 1234 Stellenbosch")
- **address**: Full street address of the property
- **city**: City/town name
- **province**: Province (Western Cape, Gauteng, KwaZulu-Natal, etc.)
- **postal_code**: Postal code if shown
- **erf_number**: Erf/stand number (e.g. "Erf 1234", "Stand 567")
- **municipal_account_number**: The municipal account number
- **property_type**: One of: apartment, house, townhouse, commercial (infer from usage/zoning)
- **owner_name**: Property owner name as shown on the bill
- **owner_id_or_reg**: Owner ID number or company registration if shown
- **zoning**: Zoning type if shown (residential, commercial, industrial, agricultural)
- **property_size_m2**: Property size in m² if shown
- **rates_amount**: Monthly rates amount in ZAR
- **refuse_amount**: Refuse/waste removal amount if shown
- **water_account**: Water meter number or account
- **electricity_account**: Electricity meter/account number if shown
- **total_due**: Total amount due
- **billing_date**: Date of the bill (ISO format)
- **due_date**: Payment due date (ISO format)

## Output

Respond ONLY with valid JSON — no markdown, no explanation:

{{
  "property_name": "",
  "address": "",
  "city": "",
  "province": "",
  "postal_code": "",
  "erf_number": "",
  "municipal_account_number": "",
  "property_type": "apartment | house | townhouse | commercial",
  "owner_name": "",
  "owner_id_or_reg": "",
  "zoning": "",
  "property_size_m2": null,
  "rates_amount": null,
  "refuse_amount": null,
  "water_account": "",
  "electricity_account": "",
  "total_due": null,
  "billing_date": "",
  "due_date": "",
  "municipality": "",
  "confidence_notes": []
}}

For `confidence_notes`, include any notes about uncertain extractions or fields you couldn't find.
Only extract what is explicitly present. Use null for missing numeric fields and "" for missing text fields."""


class ParseMunicipalBillView(APIView):
    """
    POST /api/v1/properties/parse-municipal-bill/

    Accepts a municipal bill (PDF/JPG/PNG) and returns structured property data.
    """
    permission_classes = [IsAuthenticated, IsAgentOrAdmin]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response(
                {"detail": "No file provided."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        api_key = getattr(settings, "ANTHROPIC_API_KEY", "") or ""
        if not api_key:
            return Response(
                {"detail": "ANTHROPIC_API_KEY not configured."},
                status=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Read and encode file
        data = file.read()
        mime, _ = mimetypes.guess_type(file.name)
        if not mime:
            mime = "application/octet-stream"

        if mime.startswith("image/"):
            file_block = {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": mime,
                    "data": base64.standard_b64encode(data).decode(),
                },
            }
        elif mime == "application/pdf":
            file_block = {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": base64.standard_b64encode(data).decode(),
                },
            }
        else:
            return Response(
                {"detail": f"Unsupported file type: {mime}. Upload a PDF, JPG, or PNG."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        content = [
            {
                "type": "text",
                "text": (
                    f"Extract property information from this South African municipal bill.\n"
                    f"Filename: {file.name}\n\n"
                    "Return ONLY the JSON object as specified in your instructions."
                ),
            },
            file_block,
        ]

        client = anthropic.Anthropic(api_key=api_key)
        system = SYSTEM_PROMPT.format(today=date.today().isoformat())

        try:
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
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
            extracted = json.loads(raw)
        except json.JSONDecodeError:
            return Response(
                {"detail": "Claude returned invalid JSON.", "raw": raw[:500]},
                status=http_status.HTTP_502_BAD_GATEWAY,
            )

        return Response({"extracted": extracted, "filename": file.name})
