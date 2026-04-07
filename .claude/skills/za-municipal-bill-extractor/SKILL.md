---
name: za-municipal-bill-extractor
description: >
  Extracts structured property and billing data from South African municipal bills
  (rates accounts) using Claude vision with Anthropic tool_use for guaranteed JSON output.
  Use this skill whenever: a user uploads a municipal bill, rates statement, or municipal
  account; mentions "municipal bill", "rates bill", "rates account", "municipal account",
  "erf number", "municipal statement"; wants to auto-fill property details from a bill;
  mentions any SA municipality (City of Cape Town, Stellenbosch, Drakenstein, eThekwini,
  Tshwane, Johannesburg, Nelson Mandela Bay, Buffalo City, Mangaung); or asks to extract
  property information from a utility/rates document. ALWAYS use this skill for any
  municipal bill parsing or property data extraction from SA municipal documents.
---

# SA Municipal Bill Data Extractor

You are building or maintaining the municipal bill extraction pipeline. This skill covers the backend endpoint (`POST /api/v1/properties/parse-municipal-bill/`) and frontend integration in the Add Property modal.

The core pattern: user uploads a municipal bill (PDF/JPG/PNG) -> backend sends it to Claude with **tool_use** (not free-text JSON) -> structured data returned with per-field confidence scores -> frontend auto-fills the Add Property form.

---

## Architecture

```
Frontend (PropertiesView.vue)          Backend (municipal_bill_view.py)
┌─────────────────────┐               ┌──────────────────────────────┐
│ Upload Municipal Bill│──multipart──>│ ParseMunicipalBillView       │
│                      │              │   1. Validate file (<10MB)    │
│ Auto-fill form fields│<──JSON─────  │   2. Encode file (base64)     │
│ Show confidence badges│             │   3. pypdf text extraction    │
└─────────────────────┘               │   4. Claude API (tool_use)    │
                                      │   5. Return structured data   │
                                      └──────────────────────────────┘
```

**Key files:**
- `backend/apps/properties/municipal_bill_view.py` — API endpoint
- `backend/apps/properties/extraction_utils.py` — shared tool schemas, retry logic, file encoding
- `admin/src/views/properties/PropertiesView.vue` — frontend upload + auto-fill

---

## The Critical Pattern: Anthropic tool_use (NOT Free-Text JSON)

Previous implementation asked Claude to output JSON as text, then parsed it with string manipulation. This is fragile. The correct pattern uses **tool_use with forced tool_choice**, which guarantees the response matches a defined schema.

```python
# The tool schema defines the exact structure Claude must return
MUNICIPAL_BILL_TOOL = {
    "name": "submit_municipal_bill_data",
    "description": "Submit extracted property and billing data from a South African municipal bill",
    "input_schema": { ... }  # See references/tool-schemas.md
}

# Force Claude to use this specific tool
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=4096,
    system=SYSTEM_PROMPT,
    messages=[{"role": "user", "content": content}],
    tools=[MUNICIPAL_BILL_TOOL],
    tool_choice={"type": "tool", "name": "submit_municipal_bill_data"}
)

# Response is ALREADY a dict — no JSON parsing needed
block = next(b for b in response.content if b.type == "tool_use")
extracted = block.input  # Dict matching input_schema exactly
```

This eliminates:
- Markdown fence stripping
- `json.loads()` failures
- Trailing comma issues
- Truncated JSON objects

The existing codebase already uses this pattern in `backend/apps/leases/template_views.py` (lines 1132-1580) — follow that implementation.

---

## System Prompt Design

The system prompt should NOT say "respond ONLY with valid JSON" (tool_use handles structure). Instead, focus on **domain knowledge** and **extraction guidance**.

Key elements:
1. SA municipality format knowledge (each municipality has different bill layouts)
2. Field-by-field extraction guidance with examples
3. Confidence scoring rules (when to give high vs low confidence)
4. Date and number format instructions

Read `references/sa-municipal-formats.md` for municipality-specific layout knowledge and few-shot examples.

### Confidence Score Rules

Each extracted field gets a confidence score (0-100):
- **90-100**: Value clearly printed/typed on the bill, unambiguous
- **70-89**: Value present but partially obscured, abbreviated, or requires minor interpretation
- **40-69**: Value inferred from context (e.g., property_type from zoning code)
- **0-39**: Best guess, value not explicitly on the bill

---

## File Processing Pipeline

### Step 1: Validate
```python
data = file.read()
if len(data) > 10 * 1024 * 1024:  # 10MB limit
    return Response({"detail": "File too large (max 10MB)."}, status=400)
```

### Step 2: Encode for Claude API
- **Images** (JPG/PNG): base64 encoded as `{"type": "image", "source": {"type": "base64", ...}}`
- **PDFs**: base64 encoded as `{"type": "document", "source": {"type": "base64", "media_type": "application/pdf", ...}}`

### Step 3: pypdf Text Extraction (PDFs only)
Extract text from the PDF using pypdf as **supplementary context**. This helps Claude even when the PDF has a visual/scanned layout — the extracted text provides additional signals.

```python
from pypdf import PdfReader
import io

if mime == "application/pdf":
    try:
        reader = PdfReader(io.BytesIO(data))
        pdf_text = "\n".join(
            page.extract_text() or "" for page in reader.pages[:10]
        )
        if pdf_text.strip():
            content.append({
                "type": "text",
                "text": f"[Supplementary text extracted from PDF via pypdf]\n{pdf_text[:6000]}"
            })
    except Exception:
        pass  # PDF text extraction is best-effort
```

This pattern comes from `backend/apps/leases/parse_view.py` which uses `MIN_EXTRACTED_TEXT_CHARS = 800` to decide between text-only and native PDF modes. For municipal bills, always send both the visual PDF AND extracted text.

### Step 4: Call Claude with tool_use
Use `call_claude_with_tools()` from `extraction_utils.py` (shared retry wrapper).

### Step 5: Return structured data
```python
return Response({
    "extracted": extracted,          # The tool output dict
    "filename": file.name,
    "confidence_scores": extracted.get("confidence_scores", {})
})
```

---

## Retry Logic

```python
def call_claude_with_tools(client, system, content, tool, max_retries=2, max_tokens=4096):
    """Call Claude with forced tool_use. Retries on API errors with exponential backoff."""
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": content}],
                tools=[tool],
                tool_choice={"type": "tool", "name": tool["name"]}
            )
            # Find the tool_use block
            for block in response.content:
                if block.type == "tool_use":
                    return block.input, None
            return None, "No tool_use block in response"
        except (anthropic.APIError, anthropic.RateLimitError) as exc:
            last_error = str(exc)
            if attempt < max_retries:
                import time
                time.sleep(1 * (2 ** attempt))  # 1s, 2s backoff
                continue
    return None, f"Claude API failed after {max_retries + 1} attempts: {last_error}"
```

---

## Frontend Integration

In `PropertiesView.vue`, the municipal bill upload sits at the top of the Add Property modal:

1. User clicks "Upload Municipal Bill" or drags a file
2. Frontend POSTs to `/api/v1/properties/parse-municipal-bill/` with `multipart/form-data`
3. On success, auto-fill form fields from `data.extracted`:
   - `property_name`, `address`, `city`, `province`, `postal_code`, `property_type`
4. Show confidence badges next to auto-filled fields:
   - Green badge (>=80%): `bg-success-50 text-success-700`
   - Amber badge (50-79%): `bg-warning-50 text-warning-700`
   - Red badge (<50%): `bg-danger-50 text-danger-700`
5. Show success/error state with toast notification

---

## Reference Files

- `references/tool-schemas.md` — Complete tool schema definition for `MUNICIPAL_BILL_TOOL`
- `references/sa-municipal-formats.md` — Municipality-specific bill layouts, few-shot examples, and extraction guidance
