# POPIA Cross-Border Data Transfer — s72

Any time tenant PI leaves South Africa — including cloud storage on a non-SA region — s72 applies.

## 1. The rule (s72(1))

A Responsible Party may **not** transfer PI about a data subject to a third party in a **foreign country** unless **one** of the following grounds is satisfied:

- (a) The **recipient is subject** to a law, binding corporate rules, or binding agreement providing an **adequate level of protection** materially similar to POPIA, including further transfer onward.
- (b) The **data subject consents** to the transfer.
- (c) The transfer is **necessary for performance of a contract** between the data subject and Responsible Party, or for pre-contract steps at data subject's request.
- (d) The transfer is **necessary for the conclusion or performance of a contract** concluded in the data subject's interest between the Responsible Party and a third party.
- (e) The transfer is for the **benefit of the data subject** and it is not reasonably practical to get consent; if consent were requested it would likely be given.

## 2. What counts as "adequate protection"?

POPIA does not maintain a whitelist like the EU. **Adequacy** is assessed case by case by looking at the recipient's:

- Data protection law (GDPR, UK DPA, CCPA, Singapore PDPA — commonly accepted)
- Binding corporate rules (e.g. AWS BCR, Google BCR)
- Standard contractual clauses in a written DPA

**Safe bets** as of 2025–2026:
- EU / EEA → GDPR (adequate)
- UK → UK DPA 2018 (adequate)
- Switzerland, Canada, NZ, Argentina, Japan, South Korea → generally accepted
- **USA** → grey area; adequacy depends on contractual clauses + vendor's privacy programme

## 3. Cloud hosting and SaaS — the practical gate

Every cloud/SaaS vendor used in rentals creates a transfer:

| Vendor type | Typical region | Transfer grounds |
|---|---|---|
| AWS `af-south-1` (Cape Town) | SA | No s72 transfer — domestic |
| AWS `eu-west-1` (Ireland) | EU | s72(1)(a) via GDPR + DPA |
| Azure South Africa North | SA | Domestic |
| Microsoft 365 / Google Workspace | Global | DPA + BCR |
| Credit bureaux (TPN, XDS) | SA | Domestic |
| Stripe / PayPal / Stitch | Mixed | DPA required |
| DocuSign, Adobe Sign | US/EU | DPA + BCR |
| Sentry, Datadog, Mixpanel | US/EU | DPA + BCR |

**Klikk practical**: Native signing via Gotenberg on your own infra avoids a cross-border hop. AWS in Cape Town keeps the primary data domestic. Analytics / error monitoring tools are where most unintended transfers occur.

## 4. Disclosure obligations (s18)

The **privacy notice** must disclose whether PI will be transferred to a third country and the level of protection.

**Minimum wording**: "We may transfer your personal information outside South Africa to [country/service] for [purpose]. The recipient is bound by contractual data protection clauses materially similar to POPIA."

## 5. Further transfer (onward transfer)

s72(1)(a) says the adequacy must include **further transfer** — if your US vendor sub-processes with a third party (e.g. Twilio → AWS → some sub-processor), the DPA must oblige the chain to maintain equivalent protection.

## 6. Tenant consent route (s72(1)(b))

If adequacy is doubtful, fall back to **explicit tenant consent** in the privacy notice. But:

- Consent is weak — can be withdrawn
- Cannot be bundled with lease consent
- Must name the country and the purpose

## 7. Contract necessity route (s72(1)(c)–(d))

Strong where the transfer is **inherent** to the service the tenant requested — e.g., sending a Google Calendar invite for a viewing, where the tenant chose Gmail. The contract with the tenant justifies the incidental transfer.

## 8. Regulator guidance

- **Guidance Note on Processing of PI across borders (2022)** — emphasises contractual mechanisms and recommends Standard Contractual Clauses or Model Clauses.
- No SA-specific SCCs have been published — use EU SCCs or draft bespoke clauses aligned to s72.

## 9. Breach + cross-border complication

If a US cloud vendor suffers a breach involving SA tenant data:
- Responsible Party (Klikk/landlord) must still notify under s22.
- Operator Agreement must oblige vendor to notify you promptly.
- Practical SLA: vendor notice within 24–48 hours of detection.

## 10. Founder quick-check

| Scenario | Status |
|---|---|
| Django DB on AWS Cape Town | ✅ Domestic — no s72 issue |
| Email via Google Workspace US | ⚠️ Cross-border — rely on Google's DPA + BCR; disclose in privacy notice |
| Tenant data in Mixpanel (US) | ⚠️ Consent or DPA + BCR; disclose |
| Backup to S3 Ireland | ✅ EU GDPR adequate; DPA required |
| Signed lease PDFs on DocuSign US | ⚠️ DPA + contract necessity |
| WhatsApp tenant groups (Meta, US/Ireland) | ⚠️ Meta BCR; but content-risk on PI in group chats is high |
| Sending a tenant reference to an overseas landlord | ⚠️ Tenant consent required + s72 disclosure |
