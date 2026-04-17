# POPIA Core — Act 4 of 2013

Protection of Personal Information Act — the SA equivalent of GDPR. Enforceable from **1 July 2021** (after 1-year grace period). Enforced by the **Information Regulator** (Pretoria).

## 1. Purpose

Gives effect to the constitutional right to privacy (Constitution s14). Regulates how **personal information (PI)** is **processed** by **public and private bodies**.

## 2. Key definitions (s1)

| Term | Meaning |
|---|---|
| **Personal Information (PI)** | Any information relating to an **identifiable, living natural person**, and where applicable, an existing juristic person. Includes ID, contact, biometric, financial, opinions, correspondence, inferred data. |
| **Special Personal Information** | Religion, race, health, sex life, biometrics, criminal behaviour, trade union membership, political persuasion. See `02-popia-special-pi.md`. |
| **Data Subject** | The person to whom the PI relates (tenant, applicant, guarantor, household member). |
| **Responsible Party** | The entity that **determines the purpose and means** of processing (landlord, agency). |
| **Operator** | Processes PI **on behalf of** the Responsible Party under a written contract (cloud host, credit bureau, PDF signing service). |
| **Processing** | Any operation on PI — collect, store, use, share, delete. |
| **Processing limitation** | Minimality — only what's necessary. |

## 3. The 8 Conditions for Lawful Processing (ss8–25)

The spine of POPIA. Every practice must map to all eight.

1. **Accountability (s8)** — the Responsible Party must ensure compliance.
2. **Processing Limitation (ss9–12)** — lawful, minimal, with consent or other justification; collected directly from the data subject where possible.
3. **Purpose Specification (ss13–14)** — collect for a specific, explicit, lawful purpose; retain only as long as necessary.
4. **Further Processing Limitation (s15)** — secondary use must be compatible with the original purpose.
5. **Information Quality (s16)** — accurate, complete, up to date.
6. **Openness (ss17–18)** — maintain a PAIA/POPIA Manual; notify data subjects at collection (privacy notice).
7. **Security Safeguards (ss19–22)** — appropriate technical + organisational measures; written operator agreements; breach notification.
8. **Data Subject Participation (ss23–25)** — right to access, correct, delete PI.

## 4. Lawful bases for processing (s11)

Processing is lawful only if **one of these** applies:

| s11(1) | Basis | Typical rental use |
|---|---|---|
| (a) | **Consent** — specific, informed, voluntary, revocable | Credit check, marketing, biometric access |
| (b) | **Necessary to conclude/perform a contract** with the data subject | Collecting ID to issue the lease |
| (c) | **Compliance with a legal obligation** | FICA record-keeping, tax records |
| (d) | **Protects a legitimate interest** of the data subject | Emergency maintenance access |
| (e) | **Performance of a public law duty** | Rare in private rentals |
| (f) | **Legitimate interest** of the Responsible Party or third party — subject to a balancing test | Internal fraud prevention, security monitoring |

**Founder rule of thumb**: For rental operations, most processing sits on **(b) contract** + **(c) legal obligation (FICA)**. Credit checks and marketing need **(a) consent**. Never rely on consent for things you'd do anyway — it's weak because it can be withdrawn.

## 5. Responsible Party vs Operator (ss20–21)

- **Responsible Party**: Klikk / landlord / agency — determines purpose + means.
- **Operator**: Third party processing on your behalf (AWS, credit bureau, e-sign provider, debt collector, managing sub-agent).
- **s21 requires** a **written contract** with every Operator that:
  - Establishes + maintains security safeguards
  - Processes PI only with the Responsible Party's knowledge/authorisation
  - Notifies the Responsible Party of breaches immediately

**Founder mistake**: Using cloud services, credit bureaus, or a managing agent without signing a Data Processing Agreement (DPA). Regulator treats absence of DPA as prima facie s21 breach.

## 6. Data subject rights (s5 + Chapter 3)

Data subjects are entitled to:

- Be **notified** of collection (s18) and of breaches (s22).
- **Access** their PI (s23 — free request; PAIA Form 2).
- **Correct or delete** inaccurate/excessive/out-of-date PI (s24).
- **Object** to processing, including direct marketing (s11(3) + s69).
- **Not be subject** to solely automated decision-making with legal effect (s71).
- **Complain** to the Regulator / institute civil action (s99).

## 7. Openness — Privacy Notice (s18)

When collecting PI, you must inform the data subject of:

1. The information being collected
2. Purpose of collection
3. Whether collection is voluntary or mandatory
4. Consequences of not supplying it
5. Any law that requires collection
6. Whether PI will be sent outside SA (s72 link)
7. Recipients of the PI
8. Contact details of the Responsible Party
9. The data subject's rights under POPIA

**Practical**: Your rental **application form**, **tenant portal signup**, and **viewing prospect form** all need this notice at the point of collection — not buried in a lease annexure.

## 8. Security (s19)

Responsible Party must take **appropriate, reasonable technical and organisational measures** to prevent:
- Loss, damage, unauthorised destruction
- Unlawful access or processing

Must:
- Identify all reasonably foreseeable risks
- Establish + maintain safeguards
- Regularly verify safeguards are effectively implemented
- Ensure safeguards are continually updated

**Regulation 4** (of POPIA Regulations) prescribes operator conduct in more detail.

## 9. Breach notification (s22)

If there are reasonable grounds to believe PI has been **accessed or acquired by unauthorised persons**:

- **Who to notify**: Information Regulator **AND** affected data subjects
- **When**: "As soon as reasonably possible" after discovery (Regulator guidance = within 72 hours for the regulator notice where feasible)
- **How**: Regulator — written form; data subject — in writing (email, post, prominent website notice, or direct personal contact if contact info lost)
- **Contents**: Description of breach, consequences, measures taken, recommendations to data subject, identity of the unauthorised person if known

**Delay permitted** only where a public body or Regulator determines it would impede a criminal investigation.

## 10. Information Officer (s55 + Regulations)

- **Default**: Head of the private body (CEO / principal / sole proprietor) is the Information Officer.
- **Must be registered** with the Regulator (online portal).
- **Deputy IOs** should be appointed for multi-branch agencies.
- **Duties**: Encourage compliance, deal with DSARs, ensure PAIA Manual is up to date, liaise with Regulator.

## 11. Information Regulator

- **Chair**: Adv. Pansy Tlakula (appointed 2016, re-appointed 2021).
- **Powers** (Chapter 5): Receive complaints, investigate, issue enforcement notices, impose administrative fines up to **R10 million**, refer for criminal prosecution.
- **Portal**: `inforegulator.org.za` — Information Officer registration, breach notifications, PAIA Manual submission, complaint forms.

## 12. POPIA does NOT apply to (s6–s7)

- **Purely household/personal activity** (doesn't cover commercial landlords).
- **De-identified information** that cannot be re-identified.
- **Cabinet, judicial functions**, national security intelligence.
- **Journalism** (in public interest) — partial exemption.

## 13. Quick founder checklist

| ✅ | Item |
|---|---|
| ☐ | Information Officer registered on Regulator portal |
| ☐ | PAIA/POPIA Manual published on website |
| ☐ | Privacy notice shown at every PI collection point |
| ☐ | Lawful basis mapped for every processing activity |
| ☐ | Record of Processing Activities (RoPA) maintained |
| ☐ | Signed DPAs with every operator (cloud, credit bureau, payment, e-sign) |
| ☐ | Written retention schedule (per record class) |
| ☐ | Breach response plan + template letters |
| ☐ | Consent forms for credit, marketing, biometrics, criminal checks |
| ☐ | Staff POPIA training + confidentiality clauses |

For details on what documents are needed, see `10-compliance-documents.md`.
