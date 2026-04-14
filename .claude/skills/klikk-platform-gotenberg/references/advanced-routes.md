# Gotenberg Advanced Routes & Configuration Reference

## LibreOffice → PDF

**Endpoint:** `POST /forms/libreoffice/convert`

Converts Office documents (DOCX, XLSX, PPTX, ODS, etc.) and 100+ other formats to PDF.

### Supported Formats

| Category | Formats |
|----------|---------|
| Word Processing | `.doc`, `.docx`, `.docm`, `.odt`, `.rtf`, `.txt`, `.pages`, `.wpd` |
| Spreadsheets | `.xlsx`, `.xls`, `.ods`, `.csv`, `.numbers`, `.tsv` |
| Presentations | `.pptx`, `.ppt`, `.odp`, `.key` |
| Graphics | `.svg`, `.vsd`, `.vsdx`, `.cdr`, `.dxf` |
| Images | `.jpg`, `.png`, `.gif`, `.bmp`, `.tiff`, `.webp` |
| Other | `.html`, `.epub`, `.pdf`, `.ltx` |

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `landscape` | bool | `false` | Landscape orientation |
| `singlePageSheets` | bool | `false` | Force each sheet to one page (spreadsheets) |
| `skipEmptyPages` | bool | `false` | Suppress empty pages |
| `merge` | bool | `false` | Combine multiple files into one PDF (alphanumeric order) |
| `nativePageRanges` | string | all | Page selection (e.g. `1-4`) |
| `password` | string | none | Open password-protected source files |

### Image Compression

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `losslessImageCompression` | bool | `false` | Use PNG instead of JPEG |
| `quality` | int | `90` | JPEG quality (1-100) |
| `reduceImageResolution` | bool | `false` | Scale images to target DPI |
| `maxImageResolution` | int | none | Target DPI: 75, 150, 300, 600, 1200 |

### Presentation-Specific

| Parameter | Type | Description |
|-----------|------|-------------|
| `exportNotes` | bool | Include notes in output |
| `exportNotesPages` | bool | Export notes pages (Impress only) |
| `exportOnlyNotesPages` | bool | Output only notes pages |
| `exportNotesInMargin` | bool | Embed notes in page margins |
| `exportHiddenSlides` | bool | Include hidden slides |

### Document Structure

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `updateIndexes` | bool | `true` | Refresh TOC before conversion |
| `exportBookmarks` | bool | `true` | Include PDF bookmarks |
| `exportBookmarksToPdfDestination` | bool | `false` | Create named destinations |
| `addOriginalDocumentAsStream` | bool | `false` | Embed source document |
| `exportFormFields` | bool | `true` | Create interactive form widgets |
| `allowDuplicateFieldNames` | bool | `false` | Permit repeated field names |

### Native Watermarks (LibreOffice)

| Parameter | Type | Description |
|-----------|------|-------------|
| `nativeWatermarkText` | string | Single-line text watermark |
| `nativeWatermarkColor` | int | Decimal RGB (default: 8388223) |
| `nativeWatermarkFontHeight` | int | Points (0 = auto-sized) |
| `nativeWatermarkRotateAngle` | int | Tenths of degree (450 = 45deg) |
| `nativeWatermarkFontName` | string | Font (default: Helvetica) |
| `nativeTiledWatermarkText` | string | Repeating background watermark |

### PDF Viewer Preferences

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `initialView` | int | 0 | 0=none, 1=outline, 2=thumbnails |
| `initialPage` | int | 1 | Opening page |
| `magnification` | int | 0 | 0-4 zoom mode |
| `zoom` | int | 100 | Percentage when magnification=4 |
| `pageLayout` | int | 0 | 0=single, 1=column, 2=two-col-left, 3=two-col-right |
| `openInFullScreenMode` | bool | `false` | Open in fullscreen |
| `displayPDFDocumentTitle` | bool | `true` | Show title in title bar |

---

## Merge PDFs

**Endpoint:** `POST /forms/pdfengines/merge`

Combines multiple PDF files into one. Files are merged in alphanumeric order.

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `files` | file[] | PDF files to merge (required) |
| `bookmarks` | JSON | Custom bookmarks for merged PDF |
| `autoIndexBookmarks` | bool | Auto-extract and offset existing bookmarks |
| `metadata` | JSON | XMP metadata (Author, Title, etc.) |
| `pdfa` | string | PDF/A compliance level |
| `pdfua` | bool | PDF/UA accessibility |
| `userPassword` | string | Open password |
| `ownerPassword` | string | Permissions password |
| `flatten` | bool | Flatten form fields |

### File Ordering

Files are combined alphabetically. To control order, prefix filenames with numbers:

```python
files = [
    ('files', ('01_cover.pdf', cover_bytes, 'application/pdf')),
    ('files', ('02_lease.pdf', lease_bytes, 'application/pdf')),
    ('files', ('03_audit.pdf', audit_bytes, 'application/pdf')),
]
```

---

## Split PDFs

**Endpoint:** `POST /forms/pdfengines/split`

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `files` | file[] | PDF files to split (required) |
| `splitMode` | string | `intervals` or `pages` (required) |
| `splitSpan` | string | Chunk size or page ranges (required) |
| `splitUnify` | bool | Merge extracted pages into single PDF |

### Examples

```python
# Split into 5-page chunks
data = {'splitMode': 'intervals', 'splitSpan': '5'}

# Extract pages 1-3 and 7-9
data = {'splitMode': 'pages', 'splitSpan': '1-3,7-9'}

# Extract and merge into one PDF
data = {'splitMode': 'pages', 'splitSpan': '1,3,5', 'splitUnify': 'true'}
```

**Output:** ZIP archive of split files (unless `splitUnify=true`).

---

## Health Check

**Endpoint:** `GET /health`

Returns JSON:

```json
{
  "status": "up",
  "details": {
    "chromium": {"status": "up", "timestamp": "..."},
    "libreoffice": {"status": "up", "timestamp": "..."}
  }
}
```

---

## Docker Configuration Flags

### API Settings

| Flag | Env Var | Default | Description |
|------|---------|---------|-------------|
| `--api-port` | `API_PORT` | `3000` | Listen port |
| `--api-bind-ip` | `API_BIND_IP` | `0.0.0.0` | Bind address |
| `--api-timeout` | `API_TIMEOUT` | `30s` | Request timeout |
| `--api-start-timeout` | `API_START_TIMEOUT` | `30s` | Startup timeout |
| `--api-root-path` | `API_ROOT_PATH` | `/` | Root path prefix |
| `--api-body-limit` | `API_BODY_LIMIT` | none | Max request body size |
| `--api-enable-basic-auth` | `API_ENABLE_BASIC_AUTH` | `false` | HTTP basic auth |
| `--api-disable-download-from` | `API_DISABLE_DOWNLOAD_FROM` | `false` | Disable URL downloads |

### Chromium Settings

| Flag | Env Var | Default | Description |
|------|---------|---------|-------------|
| `--chromium-restart-after` | `CHROMIUM_RESTART_AFTER` | `100` | Recycle browser after N requests |
| `--chromium-max-concurrency` | `CHROMIUM_MAX_CONCURRENCY` | `6` | Max parallel conversions |
| `--chromium-max-queue-size` | `CHROMIUM_MAX_QUEUE_SIZE` | `0` | Max queued requests (0=unlimited) |
| `--chromium-auto-start` | `CHROMIUM_AUTO_START` | `false` | Start browser on boot |
| `--chromium-start-timeout` | `CHROMIUM_START_TIMEOUT` | `20s` | Browser start timeout |
| `--chromium-allow-file-access-from-files` | `CHROMIUM_ALLOW_FILE_ACCESS_FROM_FILES` | `false` | Allow `file://` access |
| `--chromium-disable-javascript` | `CHROMIUM_DISABLE_JAVASCRIPT` | `false` | Disable JS execution |
| `--chromium-ignore-certificate-errors` | `CHROMIUM_IGNORE_CERTIFICATE_ERRORS` | `false` | Skip SSL verification |
| `--chromium-disable-web-security` | `CHROMIUM_DISABLE_WEB_SECURITY` | `false` | Disable CORS |
| `--chromium-clear-cache` | `CHROMIUM_CLEAR_CACHE` | `false` | Clear cache between requests |
| `--chromium-clear-cookies` | `CHROMIUM_CLEAR_COOKIES` | `false` | Clear cookies between requests |
| `--chromium-disable-routes` | `CHROMIUM_DISABLE_ROUTES` | `false` | Disable all Chromium routes |

### LibreOffice Settings

| Flag | Env Var | Default | Description |
|------|---------|---------|-------------|
| `--libreoffice-restart-after` | `LIBREOFFICE_RESTART_AFTER` | `10` | Recycle after N conversions |
| `--libreoffice-max-queue-size` | `LIBREOFFICE_MAX_QUEUE_SIZE` | `0` | Max queued requests |
| `--libreoffice-auto-start` | `LIBREOFFICE_AUTO_START` | `false` | Start on boot |
| `--libreoffice-disable-routes` | `LIBREOFFICE_DISABLE_ROUTES` | `false` | Disable LibreOffice routes |

### Webhook Settings

| Flag | Env Var | Default | Description |
|------|---------|---------|-------------|
| `--webhook-disable` | `WEBHOOK_DISABLE` | `false` | Disable webhook support |
| `--webhook-max-retry` | `WEBHOOK_MAX_RETRY` | `4` | Max retry attempts |
| `--webhook-retry-min-wait` | `WEBHOOK_RETRY_MIN_WAIT` | `1s` | Min wait between retries |
| `--webhook-retry-max-wait` | `WEBHOOK_RETRY_MAX_WAIT` | `30s` | Max wait between retries |
| `--webhook-client-timeout` | `WEBHOOK_CLIENT_TIMEOUT` | `30s` | Webhook call timeout |

### Logging

| Flag | Env Var | Default |
|------|---------|---------|
| `--log-level` | `LOG_LEVEL` | `info` |
| `--log-std-format` | `LOG_STD_FORMAT` | `auto` |

### Webhook Usage

Instead of waiting for the PDF response synchronously, you can provide webhook headers to have
Gotenberg POST the result to your callback URL:

| Header | Description |
|--------|-------------|
| `Gotenberg-Webhook-Url` | URL to receive the PDF |
| `Gotenberg-Webhook-Error-Url` | URL to receive errors |
| `Gotenberg-Webhook-Method` | HTTP method (default: POST) |
| `Gotenberg-Webhook-Error-Method` | Error HTTP method (default: POST) |
| `Gotenberg-Webhook-Extra-Http-Headers` | JSON headers for webhook call |

---

## Common Patterns

### Python: Merge Lease + Audit Trail as Separate PDFs

```python
import requests

def merge_pdfs(pdf_list: list[tuple[str, bytes]], gotenberg_url: str) -> bytes:
    files = [
        ('files', (name, data, 'application/pdf'))
        for name, data in pdf_list
    ]
    resp = requests.post(
        f'{gotenberg_url}/forms/pdfengines/merge',
        files=files,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.content
```

### Python: Convert DOCX to PDF

```python
def docx_to_pdf(docx_bytes: bytes, gotenberg_url: str) -> bytes:
    resp = requests.post(
        f'{gotenberg_url}/forms/libreoffice/convert',
        files={'files': ('document.docx', docx_bytes, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')},
        data={'landscape': 'false'},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.content
```

### Python: HTML to PDF with Header/Footer

```python
def html_to_pdf_with_footer(html: str, footer_html: str, gotenberg_url: str) -> bytes:
    files = {
        'files': ('index.html', html.encode(), 'text/html'),
        'footer': ('footer.html', footer_html.encode(), 'text/html'),
    }
    data = {
        'preferCssPageSize': 'true',
        'printBackground': 'true',
        'marginBottom': '0.79',  # space for footer
    }
    resp = requests.post(
        f'{gotenberg_url}/forms/chromium/convert/html',
        files=files,
        data=data,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.content
```
