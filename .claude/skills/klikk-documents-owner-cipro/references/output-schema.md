# Output Schema — owner_classification.json

---

## Base Structure

```json
{
  "entity_type": "Company",
  "entity_subtype": "Pty Ltd",
  "owned_by_trust": false,
  "trust_entity": null,
  "fica": {
    "status": "complete | incomplete | needs_review",
    "documents": [
      {
        "type": "SA ID",
        "filename": "john_smith_id.pdf",
        "extracted": {
          "full_name": "John Smith",
          "id_number": "7601015009087",
          "date_of_birth": "1976-01-01",
          "nationality": "South African",
          "document_type": "SA ID"
        },
        "status": "found"
      }
    ],
    "missing": ["Bank Confirmation Letter"],
    "flags": ["Proof of address dated 2025-11-10 — may be older than 3 months"]
  },
  "cipc": {
    "status": "complete | incomplete | needs_review",
    "documents": [
      {
        "type": "CoR14.3",
        "filename": "registration_certificate.pdf",
        "extracted": {
          "registration_number": "2018/123456/07",
          "company_name": "Acme Property (Pty) Ltd",
          "entity_type": "Pty Ltd",
          "registration_date": "2018-03-15",
          "registered_address": "12 Oak Street, Stellenbosch, 7600",
          "cipc_status": "Active"
        },
        "status": "found"
      }
    ],
    "missing": ["CoR15.1A (MOI)"],
    "flags": []
  },
  "extracted_data": {
    "registration_number": "2018/123456/07",
    "company_name": "Acme Property (Pty) Ltd",
    "directors": [
      {
        "full_name": "John Smith",
        "id_number": "7601015009087",
        "nationality": "South African",
        "appointed_date": "2018-03-15"
      }
    ],
    "address": "12 Oak Street, Stellenbosch, 7600",
    "tax_number": "1234567890",
    "vat_number": ""
  },
  "persons_graph": [...],
  "mandate_readiness": {...},
  "purchase_readiness": null,
  "classified_at": "2026-04-06T10:30:00Z"
}
```

---

## Readiness Blocks

The skill produces one readiness block per *requested* scenario. When called without an explicit scenario, default to `rental_mandate` and leave the others `null`. Never fabricate readiness for a scenario the caller didn't request — the empty slot is itself informative.

### `mandate_readiness` — rental mandate signing

See [mandate-requirements.md](mandate-requirements.md) for the source rules that populate this block.

```json
"mandate_readiness": {
  "status": "ready | missing_info | blocked",
  "required_signatories": [
    {
      "role": "director",
      "name": "JOHN MICHAEL SMITH",
      "id_number": "7601015009087",
      "authority_proof": "CoR39 + board_resolution_pending",
      "can_sign_alone": false,
      "reason": "MOI requires two directors to bind the company"
    }
  ],
  "extracted_fields": {
    "legal_name": "Acme Property (Pty) Ltd",
    "registration_number": "2018/123456/07",
    "vat_number": null,
    "tax_number": "1234567890",
    "physical_address": "12 Oak Street, Stellenbosch, 7600",
    "postal_address": null,
    "bank_payout": {
      "holder_name": "Acme Property (Pty) Ltd",
      "bank": "Standard Bank",
      "branch_code": "051001",
      "account_type": "Current",
      "account_last_4": "1234",
      "confirmation_letter_present": true
    },
    "title_deed": {
      "title_deed_number": "T12345/2018",
      "erf": "Erf 1234, Stellenbosch",
      "registered_owner_matches_entity": true
    },
    "marital_regime": null
  },
  "missing_fields": ["vat_number", "postal_address"],
  "blocking_issues": [
    "Board resolution authorising John Smith to sign the mandate has not been uploaded"
  ],
  "warnings": [
    "Proof of address dated 2026-01-02 — approaching the 3-month FICA threshold"
  ]
}
```

**Status rules:**
- `ready` — no blocking_issues, no missing required fields
- `missing_info` — missing fields or non-blocking gaps, but no legal blocker
- `blocked` — at least one blocking_issue (e.g., expired Letters of Authority, deregistered company, signer not authorised)

**Blocking issue examples (rental mandate):**
- Company status: Deregistered or in liquidation
- Letters of Authority list different trustees than those attempting to sign
- Signatory is not a director/member/trustee named in the authorising document
- Bank confirmation letter holder name does not match entity legal name
- Title deed registered owner does not match the entity being onboarded

### `purchase_readiness` — property purchase *(v2)*

Reserved for v2. Until implemented, always emit `null`. Do not populate with partial data — it signals to downstream consumers that the purchase scenario was not computed in this run.

---

---

## `trust_entity` Block (when `owned_by_trust: true`)

```json
"trust_entity": {
  "trust_name": "Smith Family Trust",
  "trust_number": "IT1234/2015",
  "urn": "12345/2015",
  "trustees": [
    {"full_name": "Jane Smith", "id_number": "7812020012089"}
  ],
  "fica": {
    "status": "incomplete",
    "documents": [],
    "missing": ["Certified ID for Jane Smith", "Proof of Trust Address"],
    "flags": []
  },
  "cipc": {
    "status": "complete",
    "documents": [
      {
        "type": "Letter of Authority",
        "filename": "letters_of_authority.pdf",
        "extracted": {},
        "status": "found"
      },
      {
        "type": "Trust Deed",
        "filename": "trust_deed.pdf",
        "extracted": {},
        "status": "found"
      }
    ],
    "missing": [],
    "flags": []
  }
}
```

---

## `persons_graph` Array

```json
"persons_graph": [
  {
    "id_number": "6809125034083",
    "full_name": "FRANCOIS PETRUS DU TOIT",
    "roles": [
      {
        "entity": "STELLENBOSCH WINE ESTATES (PTY) LTD",
        "entity_type": "Company",
        "role": "Managing Director"
      },
      {
        "entity": "THE BOLAND PROPERTY TRUST",
        "entity_type": "Trust",
        "role": "Trustee"
      }
    ],
    "fica_documents_found": ["SA ID (certified 2026-02-10)"],
    "fica_reuse_note": "ID already collected — valid for both Director and Trustee roles. No duplicate needed.",
    "joint_flag": true,
    "joint_description": "Controls both the company (as MD) and the trust that owns it (as Trustee) — beneficial ownership concentration.",
    "system_records": [
      {
        "source": "User",
        "role": "TENANT",
        "related": [
          {
            "type": "Lease (primary tenant)",
            "unit": "Unit 3, 12 Oak St",
            "status": "active"
          }
        ]
      }
    ],
    "system_note": "Active tenant at Unit 3, 12 Oak St — also director of this company being onboarded as landlord."
  },
  {
    "id_number": "7002170089080",
    "full_name": "SOPHIA ELEANOR DU TOIT",
    "roles": [
      {
        "entity": "THE BOLAND PROPERTY TRUST",
        "entity_type": "Trust",
        "role": "Trustee"
      }
    ],
    "fica_documents_found": [],
    "fica_reuse_note": null,
    "joint_flag": false,
    "joint_description": null,
    "system_records": [],
    "system_note": null
  }
]
```

---

## Status Values

| Field | Values |
|-------|--------|
| `fica.status` / `cipc.status` | `complete`, `incomplete`, `needs_review` |
| `document.status` | `found`, `missing`, `unreadable` |
| `joint_flag` | `true` = same person in multiple roles |

## Registration Number Suffixes

| Suffix | Entity type |
|--------|-------------|
| `/07` | Pty Ltd |
| `/08` | Close Corporation (CC) |
| `/21` | Non-Profit Company (NPC) |
