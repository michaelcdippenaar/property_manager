---
id: RNT-QUAL-008
stream: rentals
title: "Supplier portal UX polish + invoice submission + job status"
feature: supplier_portal
lifecycle_stage: null
priority: P2
effort: M
v1_phase: "1.0"
status: backlog
asana_gid: "1214177462321308"
assigned_to: null
depends_on: []
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Suppliers today have a thin surface — make it good enough that they actually use it instead of WhatsApping invoices. Focus: accept/decline a job, update status, submit invoice, see past jobs.

## Acceptance criteria
- [ ] Supplier login + dashboard showing: open jobs, in-progress, awaiting payment, paid
- [ ] Accept / decline a dispatched maintenance job (mobile-friendly)
- [ ] Status update with photo (in progress → complete) pushed back to agent + tenant chat
- [ ] Invoice submission: PDF upload + line items + total; agent approval flow
- [ ] Payment history + outstanding balance
- [ ] Copy matches `content/brand/voice.md`

## Files likely touched
- `admin/src/views/supplier/*` (existing — polish)
- `backend/apps/suppliers/views.py`
- `backend/apps/maintenance/supplier_api.py`

## Test plan
**Manual:**
- Create a supplier, dispatch a job, supplier accepts on phone, uploads progress pic, submits invoice, agent approves

## Handoff notes
