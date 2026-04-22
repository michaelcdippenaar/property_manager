#!/usr/bin/env python
"""
Volt Owner MCP — stdio server for Claude Desktop / Claude Code.

Launch (from the backend dir, venv active):

    VOLT_OWNER_API_KEY=volt_owner_xxx… \\
    DJANGO_SETTINGS_MODULE=config.settings.local \\
    python -m apps.the_volt.mcp.server

Or register in Claude Desktop config (~/Library/Application Support/Claude/claude_desktop_config.json):

    {
      "mcpServers": {
        "volt": {
          "command": "/absolute/path/to/.venv/bin/python",
          "args": ["-m", "apps.the_volt.mcp.server"],
          "cwd": "/absolute/path/to/backend",
          "env": {
            "VOLT_OWNER_API_KEY": "volt_owner_…",
            "DJANGO_SETTINGS_MODULE": "config.settings.local"
          }
        }
      }
    }

See apps/the_volt/mcp/README.md for full setup.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# ── Bootstrap Django before importing models ──
_backend = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_backend))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

import django  # noqa: E402

django.setup()

from fastmcp import FastMCP  # noqa: E402

from apps.the_volt.mcp.tools import read as read_tools  # noqa: E402
from apps.the_volt.mcp.tools import write as write_tools  # noqa: E402

mcp = FastMCP(
    name="volt-owner",
    instructions=(
        "The Volt — the owner's personal data sovereignty vault. "
        "Expose read + write tools scoped to a single vault owner via the "
        "VOLT_OWNER_API_KEY env var. Supports South African entity types: "
        "personal, trust, company, close_corporation, sole_proprietary, asset. "
        "All writes encrypted at rest and audited to VaultWriteAudit.\n\n"
        "SESSION START:\n"
        "  1. Call ensure_vault() to confirm the owner.\n"
        "  2. Call get_api_schema() once to discover all tools, entity types, "
        "document types, and relationship types.\n\n"
        "CREATING ENTITIES:\n"
        "  - upsert_owner (personal, convenience)\n"
        "  - upsert_property (asset, convenience)\n"
        "  - upsert_tenant (personal + optional leases_from link)\n"
        "  - upsert_entity (ANY type: company, trust, close_corporation, sole_proprietary, etc.)\n\n"
        "UPLOADING DOCUMENTS:\n"
        "  1. Call list_document_types(entity_type=...) to find the correct code.\n"
        "  2. Call get_document_type(code) for extraction_schema + upload instructions.\n"
        "  3. Extract required fields from the document into a dict.\n"
        "  4. Call attach_document(entity_id, document_type, label, file_base64, "
        "original_filename, mime_type, extracted_data).\n\n"
        "LINKING ENTITIES:\n"
        "  1. Call list_relationship_types() to find the correct code.\n"
        "  2. Call link_entities(from_entity_id, to_entity_id, relationship_type, metadata).\n\n"
        "QUERYING:\n"
        "  - list_entities, find_entity, get_entity, list_documents"
    ),
)

read_tools.register(mcp)
write_tools.register(mcp)

# ── MCP Prompts — workflow guides for agents ──


@mcp.prompt()
def document_upload_workflow() -> str:
    """Step-by-step workflow for classifying and uploading documents to the vault.

    Use this prompt when you have files to upload and need the full procedure.
    """
    return """# Vault Document Upload Workflow

## Prerequisites
1. Call `ensure_vault()` — confirm the owner session is active.
2. Call `list_entities()` — identify which entities exist in the vault.
3. If the entity doesn't exist yet, create it with `upsert_entity()`, `upsert_owner()`, or `upsert_property()`.

## Step 1: Classify the Document
- Look at the filename, folder structure, and (if readable) content.
- Call `list_document_types(entity_type=...)` to get all recognised types for the entity.
- Match the document to a catalogue code using `classification_signals`.
- If unsure, call `get_document_type(code)` for detailed classification hints.

## Step 2: Extract Metadata
- Call `get_document_type(code)` to get the `extraction_schema`.
- For each field in the schema:
  - **required=true**: MUST extract from the document. If not visible, set to `null`.
  - **required=false**: Extract if clearly visible; omit if not.
- Build an `extracted_data` dict matching the schema keys.

### Extraction by Document Type — Examples:
- **SA ID (sa_id_document)**: `{id_number, full_name, date_of_birth, gender, citizenship_status}`
- **Title Deed (title_deed)**: `{erf_number, property_description, registered_owner, registration_date, title_deed_number}`
- **Company Registration (cipc_registration_certificate)**: `{company_name, registration_number, registration_date, company_type}`
- **Trust Deed (trust_deed)**: `{trust_name, trust_number, deed_date, trust_type, trustees[], founder}`

## Step 3: Upload
```
attach_document(
    entity_id=<entity PK>,
    document_type="<catalogue code>",
    label="<Entity Name>'s <Document Label>",
    file_base64=<base64-encoded file bytes>,
    original_filename="original_name.pdf",
    mime_type="application/pdf",
    extracted_data={...}
)
```

## Step 4: Link Entities (if needed)
After upload, create relationships:
- Director → Company: `link_entities(person_id, company_id, "director_of")`
- Trustee → Trust: `link_entities(person_id, trust_id, "trustee_of")`
- Owner → Property: `link_entities(person_id, property_id, "holds_asset")`

## Tips
- **One document per call** — don't batch.
- **Label format**: "<Entity Name>'s <Document Type Label>" e.g. "MC Dippenaar's SA ID"
- **mime_type**: Use "application/pdf" for PDFs, "image/jpeg" for JPGs, "image/png" for PNGs.
- **Deduplication**: If (entity, document_type, label) already exists, a new version is created.
- **Ownership scope**: Check `ownership_scope` — `asset_bound` docs transfer with the property on sale.
"""


@mcp.prompt()
def entity_setup_workflow() -> str:
    """Step-by-step workflow for setting up a complete entity graph in the vault.

    Use this prompt when bootstrapping a vault with multiple entities and relationships.
    """
    return """# Vault Entity Setup Workflow

## Entity Types
| Type | Tool | Use for |
|------|------|---------|
| personal | `upsert_owner()` or `upsert_entity(entity_type="personal")` | People — owners, directors, trustees, tenants |
| company | `upsert_entity(entity_type="company")` | Pty Ltd, Inc companies |
| trust | `upsert_entity(entity_type="trust")` | Family/business trusts |
| close_corporation | `upsert_entity(entity_type="close_corporation")` | CCs |
| sole_proprietary | `upsert_entity(entity_type="sole_proprietary")` | Sole props |
| asset | `upsert_property()` or `upsert_entity(entity_type="asset")` | Properties, vehicles, financial assets |

## Typical Setup Order
1. **Owner** (personal): `upsert_owner(name="MC Dippenaar", id_number="...", ...)`
2. **Companies/Trusts**: `upsert_entity(entity_type="company", name="LucaNaude Pty Ltd", data={reg_number: "..."})`
3. **Properties**: `upsert_property(name="12 Dorp St", address="...")`
4. **Link**: `link_entities(owner_id, company_id, "director_of")`
5. **Documents**: Upload docs per entity (see document_upload_workflow)

## Relationship Codes (call list_relationship_types() for full list)
- `director_of` — person → company
- `trustee_of` — person → trust
- `beneficial_owner_of` — person → trust/company
- `shareholder_of` — person/company → company
- `member_of` — person → close_corporation
- `holds_asset` — person/company/trust → asset
- `operates_as` — person → sole_proprietary
- `guarantor_for` — person → company/trust
- `leases_from` — person → asset (tenant)
- `parent_of` — entity → entity (group structure)

## Data Schema Keys (per entity_type)
Call `get_api_schema()` → `entity_types` for the full schema per type.
Key fields to populate:
- **personal**: id_number, date_of_birth, email, phone, address, tax_number
- **company**: reg_number, vat_number, company_type, directors[], shareholders[]
- **trust**: trust_number, trust_type, trustees[], beneficiaries[], deed_date
- **close_corporation**: reg_number, members[], member_interest_pct{}
- **sole_proprietary**: trade_name, id_number, tax_number, vat_number
- **asset**: asset_type, address, registration_number, acquisition_date, current_value
"""


def main() -> None:
    # FastMCP defaults to stdio transport
    mcp.run()


if __name__ == "__main__":
    main()
