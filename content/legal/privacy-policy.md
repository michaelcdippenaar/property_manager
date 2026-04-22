# Klikk Privacy Policy

**Version:** 1.0  
**Effective date:** 2026-04-22  
**Last reviewed:** 2026-04-22

---

## 1. Who we are

Klikk (Pty) Ltd ("Klikk", "we", "us", "our") is a South African company that provides an AI-powered property management platform for residential rental properties.

**Responsible Party (POPIA s1):**  
Klikk (Pty) Ltd  
[Physical address — to be inserted on incorporation]  
Email: privacy@klikk.co.za  
Phone: [to be inserted]

**Information Officer (POPIA s56):**  
Name: [Information Officer name — to be confirmed]  
Email: info-officer@klikk.co.za  
Postal address: PO Box [XXX], [City], [Postal Code]

The Information Officer is registered with the Information Regulator of South Africa.

---

## 2. Scope

This Policy applies to all personal information ("PI") we process in connection with the Klikk platform, including:

- The Klikk Admin web application (app.klikk.co.za)
- The Klikk Agent mobile app (iOS / Android)
- The Klikk Tenant mobile app (iOS / Android)
- The marketing website (klikk.co.za)
- Any API integrations with third-party services listed in our Integrations register

---

## 3. What PI we collect

### 3.1 Agency / Property Manager accounts
- Contact details: full name, email address, phone number
- Business identity: agency name, CIPC registration number, VAT number, PPRA FFC number
- Location: physical and postal address
- Financial: bank account details for rental disbursements (trust account)
- Authentication credentials (hashed; never stored in plain text)

### 3.2 Property owner accounts
- Contact details: full name, email address, phone number
- Identity documents: SA ID number or passport number (FICA requirement)
- Property details: stand number, address, title deed number

### 3.3 Tenant accounts
- Contact details: full name, email address, phone number
- Identity documents: SA ID number or passport number
- Financial: monthly income, employer, occupation
- Lease details: rental amounts, payment history, lease dates
- Emergency contact details

### 3.4 Supplier accounts
- Business details: company name, VAT number, CIPC number
- Contact person: name, email, phone
- Service categories and coverage areas

### 3.5 Website visitors
- Standard web analytics (page views, referral source) — anonymised, no individual tracking
- Contact form submissions: name, email, message

---

## 4. Lawful basis for processing (POPIA s11)

We process PI on one or more of the following grounds:

| Basis | Example use |
|-------|-------------|
| Contractual necessity (s11(1)(b)) | Creating user accounts, executing lease agreements, processing maintenance requests |
| Legal obligation (s11(1)(c)) | FICA compliance, PAIA access requests, tax records |
| Legitimate interests (s11(1)(f)) | Fraud prevention, platform security, product improvement analytics |
| Consent (s11(1)(a)) | Marketing communications (opt-in); you may withdraw at any time |

---

## 5. How we use your PI

- **Platform services:** Create and manage accounts, generate leases, process maintenance requests, facilitate e-signing, send notifications.
- **AI features:** Lease generation, maintenance matching, and other AI-assisted features use anonymised or aggregated data. No PI is used to train third-party AI models without explicit consent.
- **Communications:** Transactional emails (password reset, lease events, payment reminders). Marketing only with opt-in consent.
- **Compliance:** FICA identity verification, PAIA request handling, audit logs for regulatory purposes.
- **Security:** Authentication, fraud detection, access logging.

---

## 6. Data retention (POPIA s14)

| Data category | Retention period | Reason |
|---------------|-----------------|--------|
| Lease agreements and associated PI | 5 years post lease end | SARS requirements; RHA s5 |
| Maintenance records | 3 years | Potential disputes |
| Authentication audit logs | 2 years | Security / fraud |
| Inactive user accounts | 3 years from last login, then deleted | Legitimate interests |
| Marketing consent records | Duration of consent + 3 years | Proof of consent |

Data subject to a legal hold (litigation, regulatory inquiry) will be retained until the hold is lifted.

---

## 7. Who we share your PI with

We do not sell personal information. We share PI only as follows:

- **Service providers (Operators):** AWS (af-south-1 region) for hosting; Twilio for SMS; email delivery providers. All are bound by POPIA-compliant data processing agreements.
- **Other platform participants:** Landlords see tenant PI relevant to their properties; agents see PI for properties they manage; tenants see their own PI and landlord contact details.
- **Legal requirement:** If required by a court order, subpoena, or statutory obligation.
- **Business transfers:** In the event of a merger or acquisition, PI will be transferred only with equivalent protections.

---

## 8. Cross-border transfers (POPIA s72)

Klikk stores all personal information on AWS **af-south-1 (Cape Town)** servers located in South Africa. We do not routinely transfer PI outside South Africa. Where any cross-border transfer does occur (for example, an integration with a foreign service provider), we will ensure adequate protection exists as required by POPIA s72.

---

## 9. Security measures (POPIA s19)

- All data in transit encrypted via TLS 1.2+
- All data at rest encrypted (AWS EBS/S3 AES-256)
- JWT-based authentication with token rotation
- Role-based access control; principle of least privilege
- Audit logging of all authentication and data-access events
- Regular backups with point-in-time recovery
- Penetration testing on material platform changes

---

## 10. Your rights (POPIA s23–25; PAIA)

You have the right to:

- **Access** your PI (submit a PAIA Form 2 request to info-officer@klikk.co.za)
- **Correct or delete** inaccurate PI (in-app profile edit, or email privacy@klikk.co.za)
- **Object** to processing based on legitimate interests
- **Withdraw consent** for marketing at any time (unsubscribe link in every email)
- **Data portability** — request a machine-readable export of your PI
- **Complain** to the Information Regulator of South Africa (inforeg.org.za) if you believe your rights have been violated

We will respond to DSAR (Data Subject Access Request) submissions within **30 days** of receipt.

---

## 11. Cookies and tracking

The Klikk marketing website uses minimal analytics (Plausible Analytics — privacy-first, no cookies, no cross-site tracking). The Klikk platform applications use session tokens stored in secure, httpOnly cookies. No third-party advertising trackers are used.

---

## 12. Children

The Klikk platform is not intended for use by persons under 18 years of age. We do not knowingly collect PI from children.

---

## 13. Changes to this Policy

We will publish material changes on this page at least 30 days before they take effect. If you are a registered user, we will notify you by email and require re-acknowledgement before you can continue using the platform.

Version history is maintained at `/legal/privacy` on our website.

---

## 14. Contact

**Privacy enquiries:** privacy@klikk.co.za  
**Information Officer:** info-officer@klikk.co.za  
**Information Regulator of South Africa:** inforeg.org.za | complaints.IR@justice.gov.za
