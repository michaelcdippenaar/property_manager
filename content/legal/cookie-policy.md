# Cookie Policy

**Version:** 0.1-draft
**Effective date:** 24 April 2026
**Status:** Pending attorney review — this document is a good-faith draft and will be finalised by our legal counsel.

---

## 1. What are cookies?

Cookies are small text files that a website stores on your browser or device when you visit. They help websites remember your preferences and work correctly between page visits.

South African law addresses cookies and similar tracking technologies primarily under the **Protection of Personal Information Act 4 of 2013 (POPIA)** and the **Electronic Communications and Transactions Act 25 of 2002 (ECTA s45)**. Where cookies involve the processing of personal information, POPIA applies. Where cookies involve unsolicited electronic communications, ECTA s45 governs.

---

## 2. Who we are

**Klikk (Pty) Ltd** ("Klikk", "we", "us") is the Responsible Party as defined in POPIA s1. We operate the Klikk platform and the marketing website at klikk.co.za.

**Information Officer contact:** info-officer@klikk.co.za

---

## 3. Types of cookies we use

### 3.1 First-party vs third-party

| Type | What it means |
|------|---------------|
| **First-party** | Set directly by klikk.co.za; we control them |
| **Third-party** | Set by an external service (e.g. analytics, embedded content) |

Klikk uses **first-party cookies only** on the platform application. We do not serve third-party advertising trackers.

### 3.2 Session vs persistent

| Type | Duration | Purpose |
|------|----------|---------|
| **Session** | Deleted when you close your browser | Authentication, security tokens |
| **Persistent** | Remain until expiry date or manual deletion | Preferences, consent records |

### 3.3 Essential vs analytics

| Category | Description | Can you opt out? |
|----------|-------------|-----------------|
| **Essential** | Required for the platform to function — authentication (`sessionid`, JWT tokens), CSRF protection, security tokens | No — disabling these breaks core features |
| **Analytics** | Plausible Analytics is used on the marketing website. Plausible is **cookieless** — it uses no cookies and does not track individual users across sessions. No opt-out is required because no personal information is collected. | Not applicable |

**Klikk does not use advertising, retargeting, or cross-site tracking cookies.**

---

## 4. Plausible Analytics — cookieless measurement

The klikk.co.za marketing website uses [Plausible Analytics](https://plausible.io), a privacy-first web analytics tool. Plausible:

- Does **not** use cookies or local storage
- Does **not** collect personal information or cross-site browsing history
- Does **not** track individuals across sessions
- Aggregates page views, referral sources, and device types only
- Is self-hosted in South Africa (AWS af-south-1)

Because Plausible processes no personal information, POPIA consent requirements for analytics do not apply.

---

## 5. Cookies used in the Klikk platform application

When you are logged in to the Klikk platform (app.klikk.co.za), the following cookies may be set:

| Cookie name | Type | Duration | Purpose |
|-------------|------|----------|---------|
| `access_token` | Essential (httpOnly, Secure) | Session / short-lived | JWT access token for API authentication |
| `refresh_token` | Essential (httpOnly, Secure) | 7 days | JWT refresh token for session renewal |
| `csrftoken` | Essential | Session | Cross-Site Request Forgery protection |

All platform cookies are set with `Secure` and `HttpOnly` flags where applicable, limiting exposure to scripts and insecure connections.

---

## 6. Your right to manage cookies

### 6.1 Platform cookies (essential)

Essential platform cookies cannot be individually disabled without breaking functionality. You may delete them at any time by:

- Logging out of the platform (this clears your session cookies)
- Clearing your browser's cookies and site data

### 6.2 Marketing website (Plausible — cookieless)

Because the marketing website uses Plausible Analytics (no cookies), there is nothing to opt out of for analytics purposes.

### 6.3 Browser-level cookie management

You can control cookies through your browser settings:

- **Chrome:** Settings → Privacy and security → Cookies and other site data
- **Safari:** Preferences → Privacy → Manage Website Data
- **Firefox:** Settings → Privacy & Security → Cookies and Site Data
- **Edge:** Settings → Cookies and site permissions → Cookies and site data

Blocking all cookies on app.klikk.co.za will prevent you from logging in and using the platform.

---

## 7. Lawful basis for cookie processing (POPIA s11)

Where our cookies process personal information (e.g. authentication tokens associated with your account), we rely on **contractual necessity (POPIA s11(1)(b))** — the processing is necessary to provide the service you have signed up for.

We do not rely on consent for essential cookies because disabling them makes the service inoperable. Where we rely on consent for any optional cookies in future, we will obtain it via a clear opt-in mechanism before setting them.

---

## 8. Changes to this policy

We will update this policy if we introduce new cookie types or tracking technologies. Material changes will be communicated at least **30 days** before they take effect. The updated policy will be published at klikk.co.za/legal/cookies.

---

## 9. Contact

For any questions about this Cookie Policy or how we handle your personal information, contact us at:

- **Support:** support@klikk.co.za
- **Privacy / Information Officer:** info-officer@klikk.co.za
- **Information Regulator of South Africa:** [inforeg.org.za](https://inforeg.org.za)

---

## Version history

| Version | Date | Summary |
|---------|------|---------|
| 0.1-draft | 24 April 2026 | Initial draft — pending attorney review |
