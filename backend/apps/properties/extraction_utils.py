"""
Shared utilities for AI document extraction across property management endpoints.

Provides:
- File encoding for Anthropic API (images, PDFs, text)
- Tool schemas for structured output via tool_use
- Retry wrapper with exponential backoff
- Response validation helpers
"""

import base64
import io
import mimetypes
import re
import time
from datetime import date

import anthropic

# ── File size limit ──────────────────────────────────────────────────────────
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


# ── File encoding ────────────────────────────────────────────────────────────

def encode_file(*, data: bytes, filename: str, mime: str | None = None) -> dict | None:
    """
    Return an Anthropic content block for a file.

    Accepts raw bytes + filename. Handles images (vision blocks),
    PDFs (document blocks), and text files.

    Returns None if the file type is unsupported or encoding fails.
    """
    if not mime:
        mime, _ = mimetypes.guess_type(filename)
    if not mime:
        mime = "application/octet-stream"

    try:
        if mime.startswith("image/"):
            return {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": mime,
                    "data": base64.standard_b64encode(data).decode(),
                },
            }

        if mime == "application/pdf":
            return {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": base64.standard_b64encode(data).decode(),
                },
            }

        # Text fallback
        try:
            text = data.decode("utf-8", errors="replace")[:8000]
        except Exception:
            return None
        return {"type": "text", "text": f"[File: {filename}]\n{text}"}

    except Exception:
        return None


def extract_pdf_text(data: bytes, max_pages: int = 10, max_chars: int = 6000) -> str:
    """
    Extract text from a PDF using pypdf as supplementary context.
    Returns empty string on failure (best-effort).
    """
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        pages_text = []
        for page in reader.pages[:max_pages]:
            text = page.extract_text()
            if text:
                pages_text.append(text)
        full_text = "\n".join(pages_text)
        return full_text[:max_chars]
    except Exception:
        return ""


# ── Tool schemas ─────────────────────────────────────────────────────────────

MUNICIPAL_BILL_TOOL = {
    "name": "submit_municipal_bill_data",
    "description": (
        "Submit structured property and billing data extracted from a South African "
        "municipal bill / rates account. Every field must come directly from the document. "
        "Use null for fields not found. Provide a confidence_score (0-100) for each "
        "extracted field in the confidence_scores object."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "property_name": {
                "type": ["string", "null"],
                "description": "Short property label from the address block. E.g. '4 Otterkuil Street, Karindal' or '18 Irene Park, La Colline'."
            },
            "address": {
                "type": ["string", "null"],
                "description": "Full street address: street number, name, suburb, city, postal code."
            },
            "city": {
                "type": ["string", "null"],
                "description": "City or town name."
            },
            "province": {
                "type": ["string", "null"],
                "description": "Province: Western Cape, Gauteng, KwaZulu-Natal, etc."
            },
            "postal_code": {
                "type": ["string", "null"],
                "description": "4-digit SA postal code."
            },
            "erf_number": {
                "type": ["string", "null"],
                "description": "Erf/stand/plot number as shown on bill. E.g. 'MDRIF 4087 00001', 'ERF 1234'."
            },
            "municipal_account_number": {
                "type": ["string", "null"],
                "description": "Municipal account number (7-9 digits typically)."
            },
            "property_type": {
                "type": ["string", "null"],
                "description": "apartment, house, townhouse, or commercial — infer from zoning. null if unclear."
            },
            "owner_name": {
                "type": ["string", "null"],
                "description": "Account holder / property owner name."
            },
            "owner_id_or_reg": {
                "type": ["string", "null"],
                "description": "Owner ID or company registration number if shown."
            },
            "zoning": {
                "type": ["string", "null"],
                "description": "Zoning/usage code as on bill: RES, BUS, IND, etc."
            },
            "property_size_m2": {
                "type": ["number", "null"],
                "description": "Property size in m². Convert hectares (e.g. .2067) to m² by multiplying by 10000."
            },
            "valuation": {
                "type": ["number", "null"],
                "description": "Municipal valuation in ZAR."
            },
            "rates_amount": {
                "type": ["number", "null"],
                "description": "Monthly property rates in ZAR (zero-rated, no VAT)."
            },
            "refuse_amount": {
                "type": ["number", "null"],
                "description": "Refuse/waste removal in ZAR (incl VAT)."
            },
            "sewerage_amount": {
                "type": ["number", "null"],
                "description": "Sewerage levy in ZAR (incl VAT)."
            },
            "water_amount": {
                "type": ["number", "null"],
                "description": "Total water charges in ZAR (basic + consumption, incl VAT)."
            },
            "electricity_amount": {
                "type": ["number", "null"],
                "description": "Total electricity charges in ZAR (basic + consumption, incl VAT)."
            },
            "total_due": {
                "type": ["number", "null"],
                "description": "Total amount now due in ZAR."
            },
            "water_meter_number": {
                "type": ["string", "null"],
                "description": "Water meter number."
            },
            "water_consumption": {
                "type": ["number", "null"],
                "description": "Water consumption in kilolitres."
            },
            "electricity_meter_number": {
                "type": ["string", "null"],
                "description": "Electricity meter number."
            },
            "electricity_consumption": {
                "type": ["number", "null"],
                "description": "Electricity consumption in kWh."
            },
            "billing_date": {
                "type": ["string", "null"],
                "description": "Account date in YYYY-MM-DD format."
            },
            "due_date": {
                "type": ["string", "null"],
                "description": "Payment due date in YYYY-MM-DD format."
            },
            "billing_period": {
                "type": ["string", "null"],
                "description": "Billing period, e.g. '2026/03'."
            },
            "municipality": {
                "type": ["string", "null"],
                "description": "Municipality name, e.g. 'Stellenbosch Municipality', 'City of Cape Town'."
            },
            "deposit_amount": {
                "type": ["number", "null"],
                "description": "Deposit/guarantee amount as positive number."
            },
            "confidence_scores": {
                "type": "object",
                "description": "Map of field_name to confidence score 0-100. 95-100=clearly printed. 85-94=minor interpretation. 70-84=inferred. 50-69=moderate inference. <50=uncertain.",
                "additionalProperties": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 100
                }
            },
        },
        "required": [
            "property_name",
            "address",
            "municipal_account_number",
            "owner_name",
            "total_due",
            "municipality",
            "confidence_scores",
        ],
    },
}


CLASSIFY_TOOL = {
    "name": "submit_classification",
    "description": (
        "Submit the structured FICA/CIPC classification result for South African "
        "owner/landlord documents. Include per-document confidence scores and "
        "field-level confidence in extracted_data.confidence_scores."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "entity_type": {
                "type": "string",
                "enum": ["Individual", "Company", "Trust", "CC", "Partnership"],
            },
            "entity_subtype": {
                "type": ["string", "null"],
                "description": "Pty Ltd, NPC, SOC Ltd, Ltd, or null."
            },
            "owned_by_trust": {"type": "boolean"},
            "trust_entity": {
                "type": ["object", "null"],
                "properties": {
                    "trust_name": {"type": ["string", "null"]},
                    "trust_number": {"type": ["string", "null"]},
                    "urn": {"type": ["string", "null"]},
                    "trustees": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "full_name": {"type": "string"},
                                "id_number": {"type": ["string", "null"]},
                            },
                        },
                    },
                    "fica": {"type": "object"},
                    "cipc": {"type": "object"},
                },
            },
            "fica": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["complete", "incomplete", "needs_review"],
                    },
                    "documents": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "filename": {"type": "string"},
                                "extracted": {"type": "object"},
                                "status": {"type": "string"},
                                "confidence_score": {
                                    "type": "integer",
                                    "minimum": 0,
                                    "maximum": 100,
                                },
                            },
                        },
                    },
                    "missing": {"type": "array", "items": {"type": "string"}},
                    "flags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["status", "documents", "missing", "flags"],
            },
            "cipc": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["complete", "incomplete", "needs_review"],
                    },
                    "documents": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "filename": {"type": "string"},
                                "extracted": {"type": "object"},
                                "status": {"type": "string"},
                                "confidence_score": {
                                    "type": "integer",
                                    "minimum": 0,
                                    "maximum": 100,
                                },
                            },
                        },
                    },
                    "missing": {"type": "array", "items": {"type": "string"}},
                    "flags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["status", "documents", "missing", "flags"],
            },
            "extracted_data": {
                "type": "object",
                "properties": {
                    "registration_number": {"type": ["string", "null"]},
                    "company_name": {"type": ["string", "null"]},
                    "directors": {"type": "array"},
                    "address": {"type": ["string", "null"]},
                    "tax_number": {"type": ["string", "null"]},
                    "vat_number": {"type": ["string", "null"]},
                    "representative_name": {"type": ["string", "null"]},
                    "representative_id_number": {"type": ["string", "null"]},
                    "email": {"type": ["string", "null"]},
                    "phone": {"type": ["string", "null"]},
                    "confidence_scores": {
                        "type": "object",
                        "description": "Per-field confidence 0-100.",
                        "additionalProperties": {"type": "integer"},
                    },
                },
            },
            "persons_graph": {"type": "array"},
            "classified_at": {"type": "string"},
        },
        "required": [
            "entity_type",
            "fica",
            "cipc",
            "extracted_data",
            "classified_at",
        ],
    },
}


# ── Claude API call with tool_use ────────────────────────────────────────────

def call_claude_with_tools(
    client: anthropic.Anthropic,
    system: str,
    content: list,
    tool: dict,
    *,
    max_retries: int = 2,
    max_tokens: int = 8192,
    model: str = "claude-sonnet-4-6",
) -> tuple[dict | None, str | None]:
    """
    Call Claude with forced tool_use and return (result_dict, error_string).

    Forces Claude to respond using the specified tool, guaranteeing the response
    matches the tool's input_schema. No JSON parsing needed — block.input is
    already a dict.

    Retries on API errors with exponential backoff.
    """
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": content}],
                tools=[tool],
                tool_choice={"type": "tool", "name": tool["name"]},
            )

            # Find the tool_use block in the response
            for block in response.content:
                if block.type == "tool_use":
                    return block.input, None

            # Shouldn't happen with forced tool_choice, but handle defensively
            return None, "Claude response contained no tool_use block."

        except anthropic.RateLimitError as exc:
            last_error = f"Rate limited: {exc}"
        except anthropic.APIError as exc:
            last_error = f"API error: {exc}"
        except Exception as exc:
            # Don't retry on unexpected errors
            return None, f"Unexpected error: {exc}"

        # Exponential backoff: 1s, 2s
        if attempt < max_retries:
            time.sleep(1 * (2 ** attempt))

    return None, f"Claude API failed after {max_retries + 1} attempts: {last_error}"


# ── Validation helpers ───────────────────────────────────────────────────────

SA_REG_NUMBER_PATTERNS = [
    re.compile(r"^\d{4}/\d{6}/\d{2}$"),        # YYYY/XXXXXX/07 (Pty Ltd, etc.)
    re.compile(r"^CK\d{4}/\d{2,6}$", re.I),    # CKxxxx/yy (old CC)
    re.compile(r"^IT\d{4}/\d{4}$", re.I),       # ITxxxx/yyyy (Trust)
]


def validate_classification(classification: dict) -> list[str]:
    """
    Post-extraction validation. Returns a list of warning strings (non-blocking).
    """
    warnings = []
    extracted = classification.get("extracted_data", {})

    # Check registration number format
    reg_num = extracted.get("registration_number")
    if reg_num:
        matched = any(p.match(reg_num) for p in SA_REG_NUMBER_PATTERNS)
        if not matched:
            warnings.append(
                f"Registration number '{reg_num}' does not match expected SA format "
                "(YYYY/XXXXXX/07 or CKxxxx/yy or ITxxxx/yyyy)."
            )

    # Check entity type vs registration number suffix
    entity_type = classification.get("entity_type", "")
    if reg_num and "/" in reg_num:
        suffix = reg_num.rsplit("/", 1)[-1]
        type_suffix_map = {
            "07": "Company",
            "06": "Company",
            "08": "CC",
            "21": "Company",  # NPC
        }
        expected = type_suffix_map.get(suffix)
        if expected and expected != entity_type:
            warnings.append(
                f"Registration suffix /{suffix} suggests {expected} but entity_type is {entity_type}."
            )

    # Flag empty directors for company/CC
    if entity_type in ("Company", "CC"):
        directors = extracted.get("directors", [])
        if not directors:
            warnings.append(
                f"No directors/members extracted for {entity_type} — "
                "check if CoR39/CK1 was included in the documents."
            )

    return warnings
