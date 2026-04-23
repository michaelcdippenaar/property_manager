---
discovered_by: rentals-implementer
discovered_during: RNT-SEC-006
discovered_at: 2026-04-23
priority_hint: P2
suggested_prefix: RNT-SEC
---

## What I found

The RNT-SEC-006 acceptance criterion says "JSON + PDF summary of all personal info." The ZIP export currently contains JSON files and a README.txt. A human-readable PDF cover sheet is not included.

## Why it matters

A regulator or data subject may expect a PDF they can read without a JSON viewer. A nicely formatted PDF increases perceived compliance quality and reduces support queries.

## Where I saw it

- `backend/apps/popia/services/export_service.py` — ZIP contents defined here
- AC: "JSON + PDF summary of all personal info held"

## Suggested acceptance criteria (rough)

- [ ] Export ZIP includes a `summary.pdf` generated via Gotenberg from an HTML template
- [ ] PDF includes profile data, lease count, payment summary, generation date, POPIA statement
- [ ] PDF is generated server-side (no client-side rendering)

## Why I didn't fix it in the current task

Requires Gotenberg integration (a separate service). Adding it in this task would significantly expand the diff and is not strictly required for POPIA compliance — the JSON data fully satisfies s23. Flagging for PM to schedule as a v1.1 polish item.

## PM decision

2026-04-23: Deferred — won't fix for v1. JSON export fully satisfies POPIA s23; PDF cover sheet is a polish item. Implementer's recommendation accepted. Re-raise in v1.1 backlog.
