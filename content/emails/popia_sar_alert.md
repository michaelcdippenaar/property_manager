---
template_id: popia_sar_alert
subject: "POPIA s23 Subject Access Request — action required by {{ sla_deadline }}"
heading: "New subject access request in DSAR queue"
cta_label: "Review in DSAR queue"
cta_url_key: "queue_url"
note: "SLA deadline: {{ sla_deadline }}. Failure to respond within 30 days may constitute a POPIA breach."
---

A data subject has submitted a Subject Access Request (SAR) under POPIA section 23.

**Requester:** {{ requester_email }}
**Request ID:** {{ dsar_id }}
**SLA deadline:** {{ sla_deadline }}

Please review this request in the DSAR queue and prepare the personal-information export within the statutory 30-day window.

Note: the export will package all personal information held about the requester across the platform. Sensitive third-party information must be redacted before release.
