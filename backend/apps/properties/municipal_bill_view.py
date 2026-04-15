"""
AI municipal bill parser for property onboarding.

POST /api/v1/properties/parse-municipal-bill/

Accepts a municipal bill upload (PDF/image), sends it to Claude via tool_use,
and returns structured property data extracted from the bill.
"""

import mimetypes
from datetime import date

import anthropic
from django.conf import settings
from rest_framework import parsers, status as http_status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAgentOrAdmin
from apps.properties.extraction_utils import (
    MUNICIPAL_BILL_TOOL,
    MAX_FILE_SIZE_BYTES,
    call_claude_with_tools,
    encode_file,
    extract_pdf_text,
)

SYSTEM_PROMPT = """You are an expert at reading South African municipal bills and rates accounts.

You will receive a municipal bill document (PDF or image) and must extract all property and billing data you can find.

## How to read SA municipal bills

SA municipal bills are bilingual (English/Afrikaans) and follow a standard layout:
1. **Header**: Municipality name, VAT number, contact details
2. **Account holder block**: Owner name and postal address (top-left)
3. **Account details**: Account number, date, valuation, plot/erf number
4. **Meter readings table**: Service type (W=Water, E=Electricity), meter numbers, previous/current readings, consumption
5. **Line items table**: Service charges with tariff, VAT, and amount columns
6. **Totals**: "Total monthly" or "TOTAL NOW DUE"
7. **Footer**: Payment instructions, messages

## Key field locations

- **Owner name**: First line of the account holder address block (top-left)
- **Owner postal address**: Lines 2-5 of the account holder block — this is the account holder's MAILING address, NOT necessarily the property address. For companies or landlords who own multiple properties, this will be their office/company address.
- **Property address**: Labelled "LOCATION" on the right side of the bill — this is the ACTUAL PHYSICAL PROPERTY being rated, in reversed format (e.g. "PAUL KRUGER STREET 9" means 9 Paul Kruger Street). ALWAYS use this as both `address` and `property_name`. Re-order the reversed format to normal order (number last → number first: "PAUL KRUGER STREET 9" → "9 Paul Kruger Street"). Do NOT use the name block address for `address` or `property_name`.
- **Account number**: Labelled "ACCOUNT NUMBER" or "Rekeningnr."
- **Account date**: Labelled "ACCOUNT DATE" or "Datum" — in DD/MM/YYYY format
- **Due date**: Labelled "Due Date" or "Datum Verskuldig" — convert DD/MM/YYYY to YYYY-MM-DD
- **Erf/Plot**: Labelled "PLOT" — code like "MDRIF 4087 00001" (Stellenbosch) or "ERF 1234" (Cape Town)
- **Valuation**: Labelled "VALUATION" — property value in ZAR
- **Usage/Zoning**: "RES" = Residential, "BUS" = Business, "IND" = Industrial
- **Area**: Property size — Stellenbosch shows hectares (multiply by 10000 for m²)
- **Deposit**: Labelled "DEPOSIT/GUARANTEE" — shown as credit (negative)

**CRITICAL for Stellenbosch bills:** The LOCATION field is the property address (e.g. "PAUL KRUGER STREET 9"). The name block address is the owner's postal address — these are often DIFFERENT, especially when the owner is a company. Always extract the property address from LOCATION, not the name block.

## Service line items

| Line label | Target field | Notes |
|-----------|-------------|-------|
| Rates Monthly RES / Property Rates | rates_amount | Zero-rated (no VAT) |
| Refuse Removal / Vullis | refuse_amount | Includes VAT |
| Sewerage Levy | sewerage_amount | Includes VAT |
| Water: DOM Basic + Water: DOM Cons | water_amount | Sum both, use Amount column |
| Elekt/Elect Basic + Elekt Cons | electricity_amount | Sum both, use Amount column |
| Special Rate | (note in confidence_notes) | Area-specific levy |

## Meter readings

In the meter table:
- **W** = Water meter. Consumption in kilolitres.
- **E** = Electricity meter. Consumption in kWh.

## Important rules

1. Convert ALL dates from DD/MM/YYYY to YYYY-MM-DD
2. All monetary amounts are in ZAR — return as plain numbers, no currency symbols
3. For property_size_m2: if shown in hectares (decimal like .2067), multiply by 10000
4. For deposit_amount: remove the trailing minus sign, return as positive number
5. The municipality name may not be explicitly stated — infer from:
   - VAT registration number (4700102181 = Stellenbosch Municipality)
   - Postal address on letterhead
   - Phone area code (021 = Western Cape metros)
6. Province: infer from municipality (Stellenbosch = Western Cape)
7. property_type: infer from zoning code. "RES" = house. "Sectional Title" = apartment. If unclear, use null.

## Confidence scoring

Rate each field 0-100:
- **95-100**: Clearly printed, unambiguous, exact match to a labelled field
- **85-94**: Present on bill but needs minor interpretation (e.g., address assembly from multiple lines)
- **70-84**: Requires inference from context (e.g., municipality from VAT number)
- **50-69**: Moderate inference (e.g., property_type from zoning code)
- **Below 50**: Uncertain guess — prefer null over a low-confidence value

Today's date: {today}"""


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

        data = file.read()

        if len(data) > MAX_FILE_SIZE_BYTES:
            return Response(
                {"detail": "File too large (max 10 MB)."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        mime, _ = mimetypes.guess_type(file.name)
        file_block = encode_file(data=data, filename=file.name, mime=mime)
        if file_block is None:
            return Response(
                {"detail": f"Unsupported file type. Upload a PDF, JPG, or PNG."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        content = [
            {
                "type": "text",
                "text": (
                    f"Extract all property and billing information from this South African municipal bill.\n"
                    f"Filename: {file.name}"
                ),
            },
            file_block,
        ]

        # For PDFs, also append extracted text as supplementary context
        if mime == "application/pdf":
            pdf_text = extract_pdf_text(data)
            if pdf_text.strip():
                content.append({
                    "type": "text",
                    "text": f"[Supplementary text extracted from PDF]\n{pdf_text}",
                })

        client = anthropic.Anthropic(api_key=api_key)
        system = SYSTEM_PROMPT.format(today=date.today().isoformat())

        extracted, error = call_claude_with_tools(
            client, system, content, MUNICIPAL_BILL_TOOL
        )

        if error:
            return Response(
                {"detail": error},
                status=http_status.HTTP_502_BAD_GATEWAY,
            )

        return Response({
            "extracted": extracted,
            "filename": file.name,
            "confidence_scores": extracted.get("confidence_scores", {}),
        })
