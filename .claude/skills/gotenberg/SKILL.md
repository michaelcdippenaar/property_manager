---
name: gotenberg
description: >
  Gotenberg HTML-to-PDF service expertise for the Tremly property management platform. Use this skill
  when the user asks about Gotenberg configuration, PDF generation via Docker, HTML-to-PDF conversion,
  the Gotenberg API, PDF merging/splitting, LibreOffice document conversion, PDF encryption, PDF/A
  compliance, watermarks, stamps, header/footer templates, page layout options, Chromium rendering flags,
  or troubleshooting PDF output from the Gotenberg service. Also trigger for: "gotenberg", "PDF service",
  "docker PDF", "chromium PDF", "convert HTML to PDF", "merge PDFs", "split PDF", "PDF encryption",
  "PDF/A", "PDF accessibility", "watermark PDF", "header footer PDF", "gotenberg health", "PDF not
  rendering", "gotenberg timeout", "PDF quality", "LibreOffice convert", "DOCX to PDF", "XLSX to PDF",
  or any question about the Gotenberg Docker service. Even if the user just says "the PDF looks wrong"
  or "gotenberg isn't working" — use this skill.
---

# Gotenberg — Chromium-Based PDF Service

Gotenberg is a Docker-based API that converts HTML, URLs, Markdown, and Office documents to PDF using
headless Chromium and LibreOffice. It runs as a separate service in `docker-compose.yml` and is called
from Django via HTTP POST with multipart form data.

The key advantage for Tremly: since TipTap renders in Chromium and Gotenberg uses the same Chromium
engine for PDF rendering, the PDF output is pixel-perfect identical to what users see in the lease
template editor.

## References

Read the relevant file when you need deep API detail beyond what's in this file:

| When you need... | Read |
|---|---|
| Full Chromium HTML/URL/Markdown→PDF parameters, header/footer templates, wait strategies | [chromium-routes.md](references/chromium-routes.md) |
| LibreOffice conversion, PDF merge/split, encryption, all Docker config flags | [advanced-routes.md](references/advanced-routes.md) |

## Quick Start

### Docker Setup

```yaml
# docker-compose.yml
gotenberg:
  image: gotenberg/gotenberg:8
  restart: always
  ports:
    - "3000:3000"
  command:
    - "gotenberg"
    - "--api-timeout=60s"
    - "--chromium-disable-javascript=true"
    - "--chromium-allow-file-access-from-files"
```

### Django Settings

```python
# config/settings/base.py
GOTENBERG_URL = config("GOTENBERG_URL", default="http://localhost:3000")
```

### Python Client

The Tremly client lives at `backend/apps/esigning/gotenberg.py`:

```python
from apps.esigning.gotenberg import html_to_pdf, health_check

# Convert HTML to PDF
pdf_bytes = html_to_pdf(html_string)

# Check service health
status = health_check()  # {"status": "up", "details": {...}}
```

## Core Concept: Multipart Form POST

Every Gotenberg route works the same way: send a multipart/form-data POST with files and parameters,
get PDF bytes back. No JSON API, no SDK — just HTTP.

```python
import requests

url = f'{GOTENBERG_URL}/forms/chromium/convert/html'
files = {'files': ('index.html', html_bytes, 'text/html')}
data = {'paperWidth': '8.27', 'paperHeight': '11.7', 'printBackground': 'true'}
resp = requests.post(url, files=files, data=data, timeout=60)
pdf_bytes = resp.content
```

## Primary Routes

| Route | Endpoint | Use Case |
|-------|----------|----------|
| HTML → PDF | `POST /forms/chromium/convert/html` | Lease templates, signed PDFs |
| URL → PDF | `POST /forms/chromium/convert/url` | External page capture |
| Office → PDF | `POST /forms/libreoffice/convert` | DOCX, XLSX, PPTX conversion |
| Merge PDFs | `POST /forms/pdfengines/merge` | Combine multiple PDFs |
| Split PDFs | `POST /forms/pdfengines/split` | Extract page ranges |
| Health | `GET /health` | Service status check |

## HTML → PDF: Essential Parameters

These are the parameters you'll use most often for lease PDF generation:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `paperWidth` | string | `8.5` | Page width in inches (A4 = `8.27`) |
| `paperHeight` | string | `11` | Page height in inches (A4 = `11.7`) |
| `marginTop` | string | `0.39` | Top margin in inches |
| `marginBottom` | string | `0.39` | Bottom margin in inches |
| `marginLeft` | string | `0.39` | Left margin in inches |
| `marginRight` | string | `0.39` | Right margin in inches |
| `preferCssPageSize` | bool | `false` | Honor CSS `@page { size: A4 }` rules |
| `printBackground` | bool | `false` | Include background colors/images |
| `landscape` | bool | `false` | Landscape orientation |
| `scale` | float | `1.0` | Zoom factor (0.1 to 2.0) |
| `emulatedMediaType` | string | `print` | `print` or `screen` |

When `preferCssPageSize` is `true`, the CSS `@page` rules in the HTML take precedence over
`paperWidth`/`paperHeight`. This is the recommended approach for lease templates since the CSS
already defines `@page { size: A4; margin: 2cm; }`.

## Header & Footer Templates

Send separate HTML files as `header.html` and `footer.html` in the multipart form.

Headers and footers are isolated HTML documents — the main page's CSS does not apply to them.
Gotenberg injects special CSS classes with page data:

| Class | Content |
|-------|---------|
| `.pageNumber` | Current page number |
| `.totalPages` | Total page count |
| `.title` | Document title |
| `.url` | Document URL |
| `.date` | Print date |

```html
<!-- footer.html -->
<html><head><style>
  body { font-size: 8pt; font-family: Arial; margin: 0 1cm; }
  .right { float: right; }
</style></head><body>
  <span>Lease Agreement</span>
  <span class="right">
    Page <span class="pageNumber"></span> of <span class="totalPages"></span>
  </span>
</body></html>
```

Important: add `-webkit-print-color-adjust: exact;` if you need background colors in headers/footers.

## Wait Strategies for Dynamic Content

If your HTML uses JavaScript to render content (not typical for lease PDFs), use these to delay
the PDF capture until content is ready:

| Parameter | Example | When to use |
|-----------|---------|-------------|
| `waitDelay` | `"3s"` | Fixed pause — simple but wasteful |
| `waitForExpression` | `"window.ready === true"` | JS condition — precise |

For lease templates, these are unnecessary since the HTML is static server-rendered content.

## PDF Security & Compliance

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `pdfa` | `PDF/A-1b`, `PDF/A-2b`, `PDF/A-3b` | Archival standard compliance |
| `pdfua` | `true` | Accessibility compliance (PDF/UA) |
| `userPassword` | string | Password to open PDF |
| `ownerPassword` | string | Password for edit/print permissions |
| `metadata` | JSON | Author, Title, Keywords, Copyright |

## Tremly Integration

### Current Pipeline

```
generate_lease_html(lease)  →  generate_signed_pdf(submission)
                                      ↓
                               gotenberg.html_to_pdf(html)
                                      ↓
                               PDF bytes → signed_pdf_file
```

`generate_signed_pdf()` in `backend/apps/esigning/services.py` calls Gotenberg as the primary
renderer with xhtml2pdf as fallback if Gotenberg is unavailable.

### Health Check Endpoint

`GET /api/v1/esigning/gotenberg/health/` — staff-only endpoint that proxies the Gotenberg
health check. Returns Chromium and LibreOffice engine status.

### Test PDF Endpoint

`GET /api/v1/esigning/submissions/<pk>/test-pdf/` — regenerates the signed PDF on the fly
using Gotenberg and returns it inline. Useful for testing without completing the signing flow.

## Troubleshooting

### Gotenberg not responding
- Check Docker: `docker compose ps gotenberg`
- Check health: `curl http://localhost:3000/health`
- Check logs: `docker compose logs gotenberg`
- Default timeout is 30s — increase with `--api-timeout=60s` in docker-compose command

### PDF looks different from editor
- Ensure `preferCssPageSize: true` so CSS `@page` rules are respected
- Ensure `printBackground: true` for background colors
- Check `emulatedMediaType` — use `print` for print CSS, `screen` for screen CSS
- Font differences: install custom fonts in the Gotenberg container if needed

### Page breaks not working
- Chromium respects `page-break-before`, `page-break-after`, and `break-before`/`break-after`
- TipTap PaginationPlus wrappers are converted to `page-break-after:always` divs by the pipeline
- Check that page break CSS isn't being stripped by the HTML cleanup regex

### Large PDFs timing out
- Increase `--api-timeout` in docker-compose
- Increase `timeout` parameter in `html_to_pdf()` call
- Check Chromium concurrency: `--chromium-max-concurrency` (default: 6)

### Fonts not rendering
- Gotenberg container includes standard system fonts (DejaVu, Liberation, Noto)
- For custom fonts: mount a font directory into the container or use `@font-face` with base64
- Arial/Helvetica/Times/Courier are available by default

### Assets not loading (images, CSS)
- Remote URLs: ensure the container can resolve them (use `host.docker.internal` for localhost)
- Local assets: send as additional files in multipart form — reference by filename only (flat)
- Base64 data URIs always work (signatures use this approach)

### Container resource usage
- Gotenberg image is ~1.5GB (includes Chromium + LibreOffice)
- Each concurrent PDF uses ~100-200MB RAM
- Adjust `--chromium-max-concurrency` based on available memory
- Use `--chromium-restart-after=100` to recycle browser after N requests (prevents memory leaks)
