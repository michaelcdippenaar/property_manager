# Test Hub — Issue Tracker

This directory contains one markdown file per bug found during manual testing.
Issues are discovered, documented, red-tested, fixed, and closed here.

**Never delete issue files** — they form the project's bug history.

## Workflow
See `../context/bug_workflow.md` for the full Red-Green protocol.

## Status Values
- `RED` — test written, fix not yet applied
- `FIXED` — fix applied, user confirmed, test is green

## Directories
One subdirectory per Django module:
- `leases/` — lease agreement, template, builder, clause issues
- `accounts/` — auth, permissions, OTP, OAuth issues
- `properties/` — property, unit, landlord issues
- `maintenance/` — maintenance, supplier, dispatch, quote issues
- `esigning/` — DocuSeal, PDF, audit trail issues
- `ai/` — parsing, intelligence, skills registry issues
- `tenant_portal/` — chat, heuristics, throttle issues
- `notifications/` — push, email issues
