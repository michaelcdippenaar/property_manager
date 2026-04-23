# Klikk Stage 1 Tenant Schema — Designed for Vault33 Migration

> **Version:** 1.0 · **Date:** 2026-04-18
> **Author:** MC Dippenaar / Claude
> **Context:** Dual-track product strategy (Klikk ships now, Vault33 ships in parallel)
> **Companion docs:** `/Users/mcdippenaar/PycharmProjects/vault33/docs/vault33-system-document.md`, `/Users/mcdippenaar/PycharmProjects/vault33/docs/vault33-sow.md`

---

## 1. Purpose

Klikk ships to paying customers **before** Vault33 is production-ready. Those customers' tenant PI lives in Klikk's own database during the Stage 1 window (approximately 3–6 months).

This document defines the schema, encryption, audit, and identifier conventions that make the eventual Stage 2 migration from **Klikk-owned tenant data** → **tenant-owned Vault33 vaults** a scripted migration, not a rewrite.

**Core principle: every Stage 1 design decision assumes Stage 2 will happen.**

---

## 2. The five non-negotiables

If any of these are violated, Stage 2 migration becomes expensive or impossible.

### 2.1 UUID keys for every tenant-PI entity — from day 1

Do not reference tenant PI by Klikk sequential IDs in any downstream table. Use a UUID column that will become the Vault33 entity identifier at migration time.

```python
class Tenant(models.Model):
    id = models.BigAutoField(primary_key=True)   # internal Klikk FK
    vault_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    # ↑ This UUID is what FKs from other tables must reference.
    # ↑ At Stage 2 migration, vault_id BECOMES the Vault33 entity.vault_id.
```

All other tables that reference tenant PI (`Lease`, `PaymentLedger`, `MaintenanceTicket`, `LeaseSignature`) use `tenant_vault_id` as the FK column. **Never `tenant_id`.**

### 2.2 Entity schema mirrors Vault33's `DATA_SCHEMAS`

Klikk's `Tenant`, `CompanyEntity`, `TrustEntity`, `CloseCorpEntity`, `SolePropEntity`, `AssetEntity` tables use the exact same field names and types as Vault33's corresponding `entity_type` schemas.

**Reference:** `vault33/backend/apps/the_volt/entities/models.py::DATA_SCHEMAS`.

Summarised here:

```python
PERSONAL_FIELDS = [
    "id_number", "date_of_birth", "nationality", "tax_number",
    "address", "phone", "email", "marital_status", "spouse_name",
]

COMPANY_FIELDS = [
    "reg_number", "vat_number", "company_type", "registration_date",
    "registered_address", "directors", "shareholders",
    "financial_year_end", "tax_number",
]

TRUST_FIELDS = [
    "trust_name", "trust_number", "trust_type", "master_reference",
    "trustees", "beneficiaries", "deed_date", "tax_number",
]

CLOSE_CORP_FIELDS = [
    "reg_number", "vat_number", "members", "member_interest_pct",
    "registered_address", "financial_year_end",
]

SOLE_PROP_FIELDS = [
    "owner_name", "trade_name", "id_number", "tax_number",
    "vat_number", "business_address", "fic_registered",
]

ASSET_FIELDS = [
    "asset_type", "description", "registration_number",
    "acquisition_date", "acquisition_value", "current_value",
    "insured", "insurer", "address",
]
```

**Rule:** if Klikk needs a new tenant field that isn't in this list, it's a product decision that requires updating BOTH Klikk's model AND Vault33's `DATA_SCHEMAS` in the same PR. Schema drift = migration pain.

### 2.3 Fernet encryption with identical key-derivation to Vault33

Sensitive PI fields are encrypted at rest using the same pattern Vault33 uses:

```python
# Klikk implementation (mirror Vault33's apps.the_volt.encryption.utils)
import hashlib
from cryptography.fernet import Fernet
from django.conf import settings

def _derive_landlord_key(landlord_org_id: int) -> bytes:
    """PBKDF2-HMAC-SHA256 with 100,000 iterations."""
    return hashlib.pbkdf2_hmac(
        "sha256",
        settings.SECRET_KEY.encode(),
        str(landlord_org_id).encode(),   # salt
        100_000,
        dklen=32,
    )

def encrypt_field(plaintext: str, landlord_org_id: int) -> bytes:
    key = _derive_landlord_key(landlord_org_id)
    return Fernet(base64.urlsafe_b64encode(key)).encrypt(plaintext.encode())

def decrypt_field(ciphertext: bytes, landlord_org_id: int) -> str:
    key = _derive_landlord_key(landlord_org_id)
    return Fernet(base64.urlsafe_b64encode(key)).decrypt(ciphertext).decode()
```

**Which fields are encrypted at rest:**

| Field | Encrypted? | Reason |
|---|---|---|
| `id_number`, `passport_number`, `tax_number` | ✅ YES | identity — regulatory |
| `banking_*`, `account_number`, `routing_number` | ✅ YES | financial |
| `date_of_birth` | ✅ YES | identity |
| `spouse_name`, `spouse_id_number` | ✅ YES | identity of 3rd party |
| `address`, `phone`, `email` | ⚠️ optional | consider encrypting; easier to not |
| `full_name` | ❌ NO | needed for every list view, indexing |
| `marital_status` | ❌ NO | low sensitivity |

**Rule:** at Stage 2 migration, encrypted fields transfer as ciphertext + re-wrap the DEK under the tenant-owned vault's key. This is why matching key derivation matters — the wrapped DEK format is identical.

### 2.4 Append-only audit log — format identical to Vault33's `VaultWriteAudit`

Klikk creates one write-audit row per mutation to tenant PI. Same schema, same semantics, same tamper-evidence chain.

```python
class TenantWriteAudit(models.Model):
    """
    Append-only log mirroring Vault33's VaultWriteAudit.
    DB role has INSERT only — no UPDATE/DELETE grants.
    """
    id = models.BigAutoField(primary_key=True)
    tenant_vault_id = models.UUIDField(db_index=True)  # FK to Tenant.vault_id
    operation = models.CharField(max_length=50)   # ENTITY_CREATE, ENTITY_UPDATE, DOC_ATTACH, etc.
    target_model = models.CharField(max_length=100)
    target_id = models.CharField(max_length=100)
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)
    actor = models.JSONField(default=dict)  # {user_id, ip, user_agent, session}
    lawful_basis = models.CharField(max_length=20)   # "s11(1)(a)", "s11(1)(b)", etc.
    purpose = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    # Tamper-evidence HMAC chain
    previous_hash = models.CharField(max_length=64, default="0" * 64)
    row_hash = models.CharField(max_length=64)
    hmac_signature = models.CharField(max_length=64)

    class Meta:
        default_permissions = ()   # block Django admin edits

    def save(self, *args, **kwargs):
        prior = TenantWriteAudit.objects.order_by("-id").first()
        self.previous_hash = prior.row_hash if prior else "0" * 64
        self.row_hash = hashlib.sha256(
            f"{self.previous_hash}|{self.operation}|{self.target_id}|{json.dumps(self.after, sort_keys=True)}|{self.created_at.isoformat() if self.created_at else ''}".encode()
        ).hexdigest()
        self.hmac_signature = hmac.new(
            settings.AUDIT_HMAC_KEY.encode(),
            self.row_hash.encode(),
            hashlib.sha256,
        ).hexdigest()
        super().save(*args, **kwargs)
```

**DB role enforcement** (in Postgres):
```sql
REVOKE UPDATE, DELETE ON klikk_core_tenantwriteaudit FROM klikk_app;
```

At Stage 2 migration, the audit log rows copy over 1:1 into Vault33's audit store — tenant-scoped by `tenant_vault_id`.

### 2.5 Documents use the Vault33 `DocumentTypeCatalogue` codes

Every uploaded document tagged with a `document_type_code` from Vault33's ~85-type catalogue:

```python
class TenantDocument(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant_vault_id = models.UUIDField(db_index=True)
    document_type_code = models.CharField(max_length=50)
    # ↑ MUST match a code in Vault33 DocumentTypeCatalogue, e.g.:
    #   "sa_smart_id_card", "proof_of_address", "bank_confirmation",
    #   "sars_nor", "cipc_cor14_3", "trust_deed", etc.

    label = models.CharField(max_length=255)
    file = models.FileField(upload_to=encrypted_upload_path)  # stores .enc
    original_filename = models.CharField(max_length=255)
    file_size_bytes = models.PositiveIntegerField()
    sha256_hash = models.CharField(max_length=64)  # of PLAINTEXT (pre-encryption)
    mime_type = models.CharField(max_length=100)
    extracted_data = models.JSONField(default=dict)   # optional OCR output
    uploaded_at = models.DateTimeField(auto_now_add=True)
```

**At Stage 2 migration:** these document records and their `.enc` files transfer directly into Vault33's `VaultDocument` + `DocumentVersion` tables. No re-extraction, no re-classification, no re-encryption.

**Seeding the catalogue in Klikk:** create a management command that pulls the list from Vault33's seed migration (`0005_seed_document_catalogue.py`) and inserts equivalent rows into a `klikk_core_documenttypecatalogue` table. Same codes, same labels, same extraction schemas.

---

## 3. Tables that belong to Klikk, not Vault33

Equally important — what Klikk DOES own and keeps forever:

| Table | Purpose | Migration impact |
|---|---|---|
| `Lease` | lease agreement metadata (tenant_vault_id FK, terms, dates, rent, deposit) | Stays in Klikk post-Stage 2 |
| `PaymentLedger` | rent payments, receipts | Stays in Klikk |
| `MaintenanceTicket` | maintenance requests, photos, supplier assignments | Stays in Klikk |
| `CommunicationThread` | in-app messaging, notifications | Stays in Klikk |
| `LandlordOrg` | Klikk customer accounts, billing | Stays in Klikk — this is Klikk's own customer data, not tenant data |
| `LandlordUser` | Klikk's admin users | Stays in Klikk |
| `Subscription`, `Invoice` | Klikk's own billing to landlords | Stays in Klikk |

**Rule:** if the data exists because of the *landlord-tenant relationship* (not because of the *tenant*), it's Klikk's forever. Lease terms, rent amounts, maintenance history.

---

## 4. The migration path — Stage 1 → Stage 2

### Step 1: Freeze Klikk writes to encrypted PI fields briefly (minutes)
Customers receive notice: "Your tenant data is being migrated to Vault33. 15 minutes of read-only time."

### Step 2: Stream every Klikk tenant → Vault33 entity
```python
for klikk_tenant in Tenant.objects.all().iterator():
    vault33_client.create_entity_from_existing(
        entity_type="personal",
        vault_id=klikk_tenant.vault_id,   # UUID preserved
        data=klikk_tenant.as_vault_dict(), # fields already match
        encrypted_fields=klikk_tenant.get_encrypted_blobs(),
        landlord_org_id=klikk_tenant.landlord_org_id,
    )
```
Because the UUID, schema, and encryption match, this is a bulk `INSERT ... SELECT` style operation.

### Step 3: Stream every Klikk tenant document → Vault33 `VaultDocument` + `DocumentVersion`
```python
for klikk_doc in TenantDocument.objects.all().iterator():
    vault33_client.create_document_from_existing(
        tenant_vault_id=klikk_doc.tenant_vault_id,
        document_type_code=klikk_doc.document_type_code,  # catalogue match
        label=klikk_doc.label,
        ciphertext_bytes=klikk_doc.file.read(),            # transfer as-is
        sha256_hash=klikk_doc.sha256_hash,
        extracted_data=klikk_doc.extracted_data,
        original_filename=klikk_doc.original_filename,
    )
```

### Step 4: Stream audit rows → Vault33 `VaultWriteAudit`
```python
for row in TenantWriteAudit.objects.all().iterator():
    vault33_client.append_audit(
        tenant_vault_id=row.tenant_vault_id,
        operation=row.operation,
        before=row.before,
        after=row.after,
        actor=row.actor,
        lawful_basis=row.lawful_basis,
        purpose=row.purpose,
        created_at=row.created_at,
        row_hash=row.row_hash,
        hmac_signature=row.hmac_signature,
    )
```

### Step 5: For each tenant, issue a lease-bound Grant to the landlord
```python
for klikk_lease in Lease.objects.filter(status="active"):
    vault33_client.issue_grant(
        tenant_vault_id=klikk_lease.tenant_vault_id,
        landlord_org_id=klikk_lease.landlord_org_id,
        scope=ACTIVE_LEASE_SCOPE,
        purpose="active_lease_management",
        expires_at=klikk_lease.end_date + timedelta(days=60),
        skip_tenant_consent=True,  # migration exemption, one-time
    )
```

**Note on tenant consent:** the migration is a legitimate legal basis under POPIA §11(1)(d) — protecting the legitimate interest of the data subject (their compliance records must continue to exist). Tenants are notified of the migration with a clear explanation and an opt-out path (they can leave Klikk, take their data with them).

### Step 6: Replace Klikk's tenant read paths with Vault33 client calls
Klikk code base-wide refactor: every `Tenant.objects.get(id=X).id_number` becomes `vault33_client.get_tenant(vault_id=X).data["id_number"]`.

Because the `vault_id` UUID was the foreign key all along, this is a drop-in replacement.

### Step 7: Drop Klikk's encrypted-PI columns
After a verification period (typically 30 days), run a final migration dropping:
- `Tenant.encrypted_id_number`
- `Tenant.encrypted_tax_number`
- `Tenant.encrypted_banking_*`
- `TenantDocument.file` (the `.enc` blobs)

The `Tenant` table becomes a thin stub: `{id, vault_id, landlord_org_id, created_at}` — a pointer to the Vault33 entity.

---

## 5. What the migration CAN'T fix later

Things that only work if you get them right in Stage 1:

| Issue | Impact if not solved in Stage 1 |
|---|---|
| Sequential integer IDs used as external FKs | Full-codebase FK rewrite, 1000+ lines of migration code |
| Field names that differ from Vault33 schemas | Field-by-field translation layer needed forever |
| Plaintext sensitive PI in DB | Forced re-encryption at migration, risk of exposure during transfer |
| No audit log | Cannot prove historical processing — POPIA §17 breach |
| Free-text document type column | Manual re-classification of every document at migration |
| Different encryption key derivation | Must re-encrypt all document ciphertext with a new key — huge I/O + time + risk |

These are the traps. Avoid them in Stage 1 by following §2.

---

## 6. Implementation checklist for Klikk Stage 1

Before writing the first tenant-store code in Klikk Stage 1:

- [ ] `Tenant.vault_id = UUIDField(default=uuid4, unique=True)` added
- [ ] All FKs to tenant data use `tenant_vault_id`, not integer `tenant_id`
- [ ] `DATA_SCHEMAS` mirrored from Vault33 into Klikk constants
- [ ] Fernet encryption + PBKDF2 key derivation identical to Vault33's `apps.the_volt.encryption.utils`
- [ ] `AUDIT_HMAC_KEY` in Django settings (distinct from `SECRET_KEY`, stored in Secrets Manager at deploy)
- [ ] `TenantWriteAudit` model with append-only DB role (no UPDATE/DELETE grants)
- [ ] `DocumentTypeCatalogue` seeded from Vault33's `0005_seed_document_catalogue.py`
- [ ] `TenantDocument.document_type_code` validated against catalogue on save
- [ ] Django migration to REVOKE UPDATE/DELETE on audit table from the app's DB role
- [ ] Unit tests for encryption round-trip, audit HMAC chain, UUID uniqueness
- [ ] Migration playbook document (draft now, execute Stage 2) — step-by-step with rollback

---

## 7. Governance commitments

Written into every Stage 1 landlord DPA — these bind Klikk to the Stage 2 migration:

1. **Timeline:** "Tenant PI collected under Klikk Stage 1 will be migrated to Vault33 (tenant-owned vault model) within 12 months of lease commencement."
2. **Notification:** "Tenants receive 30 days' written notice of migration, with an option to export their data to their own private vault instead of landlord-held."
3. **No degradation:** "Post-migration, landlord's ability to access tenant data for lease operation is preserved via a Gateway grant — no functional loss."
4. **Audit continuity:** "All audit records from Stage 1 are preserved in Vault33 — chain of custody is unbroken."

These commitments prevent the "we'll migrate eventually" trap by making the migration contractual, not aspirational.

---

## 8. Decision log

| Date | Decision | Reason |
|---|---|---|
| 2026-04-18 | Dual-track product strategy confirmed (Klikk Stage 1 ships before Vault33 Stage 2) | Revenue now, optionality later |
| 2026-04-18 | Klikk Stage 1 schema mirrors Vault33 entity schemas | Migration must be INSERT ... SELECT, not translation |
| 2026-04-18 | UUID keys for all tenant PI from day 1 | Stage 2 migration preserves all external FKs |
| 2026-04-18 | Identical Fernet + PBKDF2 key derivation | Stage 2 document transfer is bit-for-bit |
| 2026-04-18 | Same `DocumentTypeCatalogue` codes in Klikk as Vault33 | No re-classification at migration |
| 2026-04-18 | `TenantWriteAudit` append-only with HMAC chain | POPIA §17 compliance from Stage 1, bit-for-bit transfer to Vault33 |
| 2026-04-18 | Migration timeline contractual in every DPA | Prevents "we'll do it eventually" trap |
