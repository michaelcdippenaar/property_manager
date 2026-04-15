# PDF Troubleshooting

---

## Merge Fields Not Being Replaced

- Check field names in template match exactly what `build_lease_context()` returns
- The regex handles both attribute orderings (`data-type` before/after `data-field-name`)
- Mustache markers (`{{field}}`) are replaced as a final pass
- In native mode, unfilled fields are preserved as spans — this is intentional

---

## Page Breaks Not Working in PDF

- Chromium supports `page-break-before`, `page-break-after`, and `break-before`/`break-after`
- TipTap PaginationPlus wrappers are converted to `page-break-after:always` divs
- Verify `preferCssPageSize` is `true` so CSS `@page` rules are respected

---

## Signatures Not Appearing in PDF

- Signature `imageData` must be a valid base64 data URL (`data:image/png;base64,...`)
- The regex matches `<signature-field name="X">` — field names must match exactly
- Check `signer['signed_fields']` has correct `fieldName` and `fieldType`

---

## PDF Layout Issues

- Gotenberg renders with full Chromium — flexbox and grid work fine
- `emulatedMediaType` should be `print`
- `printBackground: true` for background colors/images
- Use `pt` units for font sizes for consistent rendering
- Wide tables: `width:100%` and `word-break:break-all` for long text

---

## Gotenberg Not Responding

```bash
docker compose ps gotenberg
curl http://localhost:3000/health
docker compose logs gotenberg
```

Pipeline will automatically fall back to xhtml2pdf — check Django logs for the warning. Default timeout is 60s; increase in `gotenberg.py` or `docker-compose.yml`.

---

## PDF Quality Degraded (xhtml2pdf Fallback Active)

Log shows: `"Gotenberg PDF generation failed, falling back to xhtml2pdf"`

xhtml2pdf limitations vs Gotenberg/Chromium:
- No flexbox, grid, or advanced CSS3 selectors
- No remote URLs for images (must be base64 data URLs)
- Limited font support
- Complex nested tables can break

Fix: restore the Gotenberg Docker service.

---

## Adding a New Merge Field

1. Add field to `build_lease_context()` in `backend/apps/esigning/services.py`
2. Add matching `MergeField` node in the TipTap template editor
3. Field will be auto-replaced during `generate_lease_html()`
