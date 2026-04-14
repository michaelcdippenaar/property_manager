# Gotenberg Chromium Routes — Complete API Reference

## HTML → PDF

**Endpoint:** `POST /forms/chromium/convert/html`

### Required Files

| File | Description |
|------|-------------|
| `index.html` | The HTML document to convert |

### Optional Files

| File | Description |
|------|-------------|
| `header.html` | Header template (rendered on every page) |
| `footer.html` | Footer template (rendered on every page) |
| Additional files | Images, fonts, CSS — referenced by filename only (flat) |

### Page Layout

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `paperWidth` | string | `8.5` | Width in inches (A4 = `8.27`). Accepts `in`, `pt`, `cm` |
| `paperHeight` | string | `11` | Height in inches (A4 = `11.7`) |
| `marginTop` | string | `0.39` | Top margin in inches |
| `marginBottom` | string | `0.39` | Bottom margin in inches |
| `marginLeft` | string | `0.39` | Left margin in inches |
| `marginRight` | string | `0.39` | Right margin in inches |
| `landscape` | bool | `false` | Landscape orientation |
| `scale` | float | `1.0` | Zoom factor (0.1–2.0) |
| `singlePage` | bool | `false` | Force all content onto one long page |
| `preferCssPageSize` | bool | `false` | Use CSS `@page { size }` instead of paperWidth/Height |

### Rendering

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `printBackground` | bool | `false` | Include background colors/images |
| `omitBackground` | bool | `false` | Allow transparency (requires printBackground) |
| `emulatedMediaType` | string | `print` | `print` or `screen` media emulation |
| `nativePageRanges` | string | all | Page selection, e.g. `1-5, 8, 11-13` |

### Wait Strategies

| Parameter | Type | Description |
|-----------|------|-------------|
| `waitDelay` | string | Fixed pause before render (e.g. `3s`, `500ms`) |
| `waitForExpression` | string | JS expression that must return truthy (e.g. `window.ready === true`) |
| `waitForSelector` | string | CSS selector that must exist in DOM |

### HTTP & Networking

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cookies` | JSON | none | Array of cookie objects for the page |
| `extraHttpHeaders` | JSON | none | Custom headers with optional scope regex |
| `userAgent` | string | default | Override User-Agent header |
| `failOnHttpStatusCodes` | JSON | `[499,599]` | HTTP status codes that cause failure |
| `failOnResourceHttpStatusCodes` | JSON | none | Asset status codes that cause failure |
| `ignoreResourceHttpStatusDomains` | JSON | none | Domains excluded from resource checks |
| `failOnResourceLoadingFailed` | bool | `false` | Fail if any asset can't load |
| `failOnConsoleExceptions` | bool | `false` | Fail on JS console errors |
| `skipNetworkIdleEvent` | bool | `true` | Don't wait for 0 network connections |
| `skipNetworkAlmostIdleEvent` | bool | `true` | Don't wait for ≤2 network connections |

### Emulated Media Features

`emulatedMediaFeatures` — JSON array to simulate browser conditions:

```json
[{"name": "prefers-color-scheme", "value": "dark"}]
```

Supported: `prefers-color-scheme`, `prefers-reduced-motion`, `color-gamut`, `forced-colors`

### Document Structure

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `generateDocumentOutline` | bool | `false` | Create PDF bookmarks from headings |
| `generateTaggedPdf` | bool | `false` | Embed accessibility tags |
| `metadata` | JSON | none | XMP metadata: Author, Title, Keywords, Copyright |

### PDF Standards & Security

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `pdfa` | string | none | `PDF/A-1b`, `PDF/A-2b`, or `PDF/A-3b` |
| `pdfua` | bool | `false` | PDF/UA accessibility compliance |
| `userPassword` | string | none | Password required to open PDF |
| `ownerPassword` | string | none | Password for permissions (print/copy/edit) |
| `flatten` | bool | `false` | Convert form fields to static content |

### Watermark & Stamp

| Parameter | Type | Description |
|-----------|------|-------------|
| `watermarkSource` | string | `text`, `image`, or `pdf` |
| `watermarkExpression` | string | Content text or filename |
| `watermarkPages` | string | Page ranges (e.g. `1-3`) |
| `watermarkOptions` | JSON | Font, color, rotation, opacity, scaling |
| `stampSource` | string | `text`, `image`, or `pdf` |
| `stampExpression` | string | Content text or filename |
| `stampPages` | string | Page ranges |
| `stampOptions` | JSON | Font, color, rotation, opacity, scaling |

### Split & Rotation

| Parameter | Type | Description |
|-----------|------|-------------|
| `splitMode` | string | `intervals` or `pages` |
| `splitSpan` | string | Chunk size or page ranges |
| `splitUnify` | bool | Merge split pages into single PDF |
| `rotateAngle` | int | `90`, `180`, or `270` degrees |
| `rotatePagesPages` | string | Page ranges to rotate |

### Response Headers

| Header | Description |
|--------|-------------|
| `Gotenberg-Output-Filename` | Set custom output filename |
| `Gotenberg-Trace` | Request correlation ID |

## Header & Footer Templates

Headers and footers are separate HTML documents with important constraints:

1. **Isolated rendering** — main page CSS does NOT apply
2. **No external assets** — everything must be inline
3. **No JavaScript** — scripts don't execute
4. **Auto-injected classes** — Gotenberg injects page data:

| Class | Injected Value |
|-------|---------------|
| `.pageNumber` | Current page number |
| `.totalPages` | Total page count |
| `.title` | Document `<title>` |
| `.url` | Document URL |
| `.date` | Print date |

### Example Footer

```html
<!DOCTYPE html>
<html><head>
<style>
  body {
    font-size: 8pt;
    font-family: Arial, sans-serif;
    margin: 0 2cm;
    -webkit-print-color-adjust: exact;
  }
  .container { display: flex; justify-content: space-between; width: 100%; }
</style>
</head><body>
<div class="container">
  <span>Lease Agreement - Tremly Property Management</span>
  <span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>
</div>
</body></html>
```

### Example Header

```html
<!DOCTYPE html>
<html><head>
<style>
  body {
    font-size: 7pt;
    font-family: Arial, sans-serif;
    color: #999;
    margin: 0 2cm;
    border-bottom: 0.5pt solid #ddd;
    padding-bottom: 4pt;
  }
</style>
</head><body>
  <span>CONFIDENTIAL — For authorized signatories only</span>
</body></html>
```

## URL → PDF

**Endpoint:** `POST /forms/chromium/convert/url`

Same parameters as HTML → PDF, except:
- Instead of `index.html` file, send `url` (string) as the target URL
- Network parameters (cookies, headers, status codes) are more relevant here
- Supports SPAs and JavaScript-rendered pages via wait strategies

## Markdown → PDF

**Endpoint:** `POST /forms/chromium/convert/markdown`

Send:
- `index.html` — wrapper template containing `{{ toHTML .filename }}` Gotenberg template syntax
- One or more `.md` files — Gotenberg converts to HTML and injects into the template

Same rendering parameters as HTML → PDF.

## Screenshots

**HTML:** `POST /forms/chromium/screenshot/html`
**URL:** `POST /forms/chromium/screenshot/url`
**Markdown:** `POST /forms/chromium/screenshot/markdown`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `format` | string | `png` | `png`, `jpeg`, or `webp` |
| `quality` | int | 100 | JPEG/WebP quality (0-100) |
| `optimizeForSpeed` | bool | `false` | Faster but lower quality |
| `clip` | bool | `false` | Clip to viewport |
| `clipWidth` | float | viewport | Clip region width |
| `clipHeight` | float | viewport | Clip region height |
| `clipX` | float | 0 | Clip region X offset |
| `clipY` | float | 0 | Clip region Y offset |

## Response Codes

| Code | Meaning |
|------|---------|
| `200` | Success — PDF bytes in response body |
| `400` | Invalid input (bad parameters, missing files) |
| `403` | Forbidden URL |
| `409` | Conflict (e.g., Chromium not available) |
| `503` | Timeout exceeded |

## Asset Reference Rules

When sending additional files (images, fonts, CSS), reference them by filename only:

```html
<!-- Correct -->
<img src="logo.png" />
<link rel="stylesheet" href="styles.css" />

<!-- Wrong — subdirectory paths don't work -->
<img src="/images/logo.png" />
<img src="assets/logo.png" />
```

For remote resources, ensure the container can reach them. Use `host.docker.internal` instead
of `localhost` when referencing services on the Docker host.

Base64 data URIs always work and don't require network access — this is why Tremly embeds
signature images as `data:image/png;base64,...`.
