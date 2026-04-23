---
template_id: popia_rtbf_alert
subject: "POPIA s24 Erasure Request — action required by {{ sla_deadline }}"
heading: "New erasure request in DSAR queue"
cta_label: "Review in DSAR queue"
cta_url_key: "queue_url"
note: "SLA deadline: {{ sla_deadline }}. Failure to respond within 30 days may constitute a POPIA breach."
---

A data subject has submitted a Right-to-Be-Forgotten (erasure) request under POPIA section 24.

**Requester:** {{ requester_email }}
**Request ID:** {{ dsar_id }}
**SLA deadline:** {{ sla_deadline }}

Please review this request in the DSAR queue and either approve or deny it with a documented reason within the statutory 30-day window.

Note: approval will immediately anonymise the account. Lease, payment, and audit records are retained per FICA/RHA/SARS retention rules.
