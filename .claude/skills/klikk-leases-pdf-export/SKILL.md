---
name: klikk-leases-pdf-export
description: >
  Convert TipTap lease template HTML to PDF in the Tremly property management platform. Use this
  skill when the user asks about PDF generation from lease templates, HTML-to-PDF rendering,
  the merge field replacement pipeline, signature embedding in PDFs, audit trail generation,
  Gotenberg configuration, Chromium PDF rendering, print CSS for leases, or troubleshooting
  the lease PDF output. Also trigger for: "generate PDF", "lease PDF", "PDF export",
  "PDF not rendering", "signed PDF", "audit trail", "gotenberg", "chromium", "merge fields
  not filling", "PDF layout", "page breaks in PDF", "signature in PDF", "download lease",
  "PDF styling", or any question about how TipTap content becomes a downloadable/signable PDF.
  Even if the user just says "the PDF looks wrong" or "merge fields aren't being replaced" —
  use this skill.
---

# TipTap-to-PDF Pipeline

3-stage pipeline: template rendering → native signing → Gotenberg PDF.

## Key Files

| File | Purpose |
|------|---------|
| `backend/apps/esigning/services.py` | All PDF pipeline functions |
| `backend/apps/esigning/gotenberg.py` | Gotenberg Python client |
| `backend/apps/leases/models.py` | `LeaseTemplate` (v2 JSON envelope) |
| `backend/apps/leases/template_views.py` | `_extract_html()` — parses envelope |
| `backend/apps/esigning/models.py` | `ESigningSubmission` (HTML snapshot) |

> For deep Gotenberg API details, see the `klikk-platform-gotenberg` skill.

---

## Pipeline Summary

```
LeaseTemplate.content_html (v2 JSON envelope)
  ↓  generate_lease_html(lease)      services.py:422  — fill merge fields, map signers
  ↓  create_native_submission()      services.py:655  — snapshot, signers, SHA-256 hash
  ↓  Signers sign via Vue UI (/sign/<uuid>/)
  ↓  generate_signed_pdf(submission) services.py:978  — embed sigs, audit trail
  ↓  gotenberg.html_to_pdf(html)     Chromium → pixel-perfect PDF
```

---

## Reference Index

| Topic | File |
|-------|------|
| Stage 1 (generate_lease_html, build_lease_context, print CSS), Stage 2 (native submission), Stage 3 (generate_signed_pdf, Gotenberg/xhtml2pdf) | [pipeline.md](references/pipeline.md) |
| Merge fields not replaced, page breaks, signatures missing, layout issues, Gotenberg down | [troubleshooting.md](references/troubleshooting.md) |
