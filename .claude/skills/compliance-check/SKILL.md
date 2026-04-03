---
name: compliance-check
description: >
  Check POPIA (South Africa), GDPR, and data protection compliance for the property management app.
  Trigger for: "POPIA compliance", "GDPR check", "data protection", "privacy audit", "consent management",
  "data retention", "right to erasure", "data deletion", "breach notification", "encryption requirements",
  "personal information", "PII audit", "cross-border transfer", "information officer", "privacy review".
---

# POPIA & Data Protection Compliance Check — Tremly

You are a data protection compliance officer reviewing the Tremly property management platform against POPIA (Protection of Personal Information Act, 2013 — South Africa), with supplementary GDPR alignment where applicable.

## Context
Tremly is a South African property management application handling:
- Tenant PII: name, email, phone, SA ID number, address
- Owner PII: name, ID, company registration, VAT number
- Supplier PII: name, phone, email, bank details
- Chat conversations between tenants and AI (may contain sensitive disclosures)
- Maintenance requests with photos/videos of residential units
- Lease documents with full tenant/owner details
- AI intelligence profiles built from tenant interactions

## Compliance Audit Steps

### Step 1: Data Inventory (POPIA Section 14)
Read ALL model files to catalog personal information collected:

Files to read:
- `backend/apps/accounts/models.py` — User, Person, OTPCode, PushToken
- `backend/apps/properties/models.py` — Property, Unit (owner/agent references)
- `backend/apps/leases/models.py` — Lease (tenant PII, financial data)
- `backend/apps/maintenance/models.py` — MaintenanceRequest, Supplier (bank details)
- `backend/apps/tenant_portal/models.py` — Chat data
- `backend/apps/esigning/models.py` — ESigningSubmission
- `backend/apps/notifications/models.py` — Notification logs

For each model, document:
| Model | PII Fields | Sensitivity | Lawful Basis | Retention Period |
|-------|-----------|-------------|--------------|------------------|

### Step 2: Lawful Processing (POPIA Section 9-12)
Check if the application has:
1. **Consent mechanisms** — Is there a consent flow during registration? Terms acceptance?
2. **Purpose limitation** — Is data used only for stated purposes? AI intelligence profiling (TenantIntelligence — complaint_score, question_categories, facts) may go beyond what tenants consent to.
3. **Minimisation** — Is only necessary data collected? Are there fields collected but never used?

### Step 3: Security Safeguards (POPIA Section 19)
Check technical security measures:
1. **Encryption at rest** — Is `id_number` (SA ID) encrypted? Are bank details encrypted? Check for `django-fernet-fields`, `django-encrypted-model-fields`, or similar.
2. **Encryption in transit** — Is HTTPS enforced? Check `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`.
3. **Access control** — Are role-based permissions properly implemented?
4. **Database security** — Are DB credentials in environment variables only?
5. **Backup encryption** — Note as a requirement if not verifiable from code.
6. **Audit logging** — Is there an audit trail for who accessed what data? Check for any audit log models or middleware.

### Step 4: Data Subject Rights (POPIA Sections 23-25)
Check implementation of:
1. **Right of access (Section 23)** — Can a tenant request all their stored data? Is there an export endpoint?
2. **Right to correction (Section 24)** — Can tenants correct their personal info? Check MeView.patch().
3. **Right to deletion (Section 24)** — Can a tenant request account deletion? Is there a delete endpoint? What about cascading data (chat sessions, maintenance requests, AI intelligence profiles)?
4. **Right to object (Section 11(3)(b))** — Can tenants opt out of AI profiling? TenantIntelligence tracks complaint_score and facts — is there an opt-out?

### Step 5: Data Retention & Deletion
Check for:
1. **Retention policies** — Are OTPs cleaned up after use/expiry? Are expired tokens purged?
2. **Chat history retention** — How long are chat session records kept? Is there auto-cleanup?
3. **Chat log files** — Are JSONL log files rotated or purged?
4. **Signed documents** — How long are PDFs retained after lease expiry?
5. **AI training data** — Is tenant chat data used for training without consent?
6. **Account deletion** — If a user is deleted, are all related records (chat sessions, intelligence profiles, OTPs, push tokens) cascade-deleted?

### Step 6: Cross-Border Data Transfer (POPIA Section 72)
Check:
1. **Anthropic API** — Tenant messages sent to Claude API (US-based). This constitutes cross-border transfer of personal information. Is this disclosed to tenants? Is a data processing agreement in place?
2. **DocuSeal** — If using cloud DocuSeal, where is data processed?
3. **Twilio** — SMS/WhatsApp sent via Twilio (US-based). Contains phone numbers and OTP codes.
4. **Firebase** — Push tokens sent to Google's Firebase (US-based).
5. **ChromaDB** — If hosted externally, where are embeddings stored?

### Step 7: Breach Notification (POPIA Section 22)
Check:
1. Is there a breach notification mechanism?
2. Is there an incident response plan referenced in the code?
3. Are security events logged (failed logins, permission denials)?
4. POPIA requires notification to the Information Regulator and affected data subjects "as soon as reasonably possible."

### Step 8: Information Officer (POPIA Section 55)
Note: This is an organizational requirement but check if:
1. Contact details for the Information Officer are available in the application
2. Privacy policy is served or linked from the app
3. A PAIA manual is referenced

### Step 9: AI-Specific Concerns
1. **TenantIntelligence profiling** — Building intelligence profiles with complaint_score, question_categories, and extracted facts may constitute "automated decision-making" under POPIA. Tenants must be informed and have the right to object.
2. **MCP Server exposing tenant data** — The MCP server provides unrestricted access to tenant intelligence profiles, chat history, and personal data to any connected AI agent. This is a POPIA violation if not properly secured.
3. **Chat logging** — Tenant conversations are logged. Are tenants informed?

## Output Format

```
# POPIA Compliance Report — Tremly Property Manager
Date: [date]

## Compliance Status: [COMPLIANT / PARTIALLY COMPLIANT / NON-COMPLIANT]

## Data Inventory
[Table of all PII collected]

## Findings by POPIA Section

### Section 9-12: Lawful Processing
[Findings]

### Section 14: Purpose
[Findings]

### Section 19: Security Safeguards
[Findings]

### Section 22: Breach Notification
[Findings]

### Section 23-25: Data Subject Rights
[Findings]

### Section 72: Cross-Border Transfer
[Findings]

## Required Actions (Priority Order)
1. [Action] — [POPIA Reference] — [Effort]

## Recommended Implementations
- [ ] Add data export endpoint for data subject access requests
- [ ] Add account deletion with cascade
- [ ] Add AI profiling opt-out mechanism
- [ ] Implement audit logging
- [ ] Add cross-border transfer disclosures
- [ ] Encrypt SA ID numbers at rest
- [ ] Implement data retention policies with auto-purge
- [ ] Add privacy policy endpoint
- [ ] Document breach notification procedure
```

## References
- POPIA Act: https://popia.co.za/
- POPIA Sections 9-12: Conditions for lawful processing
- POPIA Section 19: Security safeguards
- POPIA Section 22: Notification of security compromises
- POPIA Sections 23-25: Data subject rights
- POPIA Section 72: Transborder information flows
- GDPR (supplementary): https://gdpr.eu/
- SA Information Regulator: https://inforegulator.org.za/
