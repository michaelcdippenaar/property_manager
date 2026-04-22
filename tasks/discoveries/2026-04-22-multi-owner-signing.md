---
discovered_by: rentals-implementer
discovered_during: RNT-QUAL-005
discovered_at: 2026-04-22
priority_hint: P2
suggested_prefix: RNT-QUAL
---

## What I found

The task spec calls for "multi-owner signatures: all owners must sign before active; if one rejects →
mandate rejected, agent notified." The current `RentalMandate` model supports exactly one owner signer
(derived from `mandate.landlord` or the current `PropertyOwnership`). There is no mechanism to attach
multiple owners, track per-owner signing status, or auto-transition to `rejected` on a rejection.

## Why it matters

Properties co-owned by multiple individuals (e.g. spouses, joint-venture partners) cannot legally be
managed under a mandate signed by only one owner. The current e-signing flow will send the mandate to
a single email address and mark it active once that person and the agent have both signed — silently
bypassing the co-owner.

## Where I saw it

- `backend/apps/properties/models.py` — `RentalMandate.landlord` is a single FK to `Landlord`.
- `backend/apps/properties/mandate_services.py:build_mandate_signers` — builds exactly 2 signers (owner + agent).
- `backend/apps/esigning/models.py` — `ESigningSubmission.signers` is a JSONField list; supports N signers but the mandate flow never populates more than one owner.

## Suggested acceptance criteria (rough)

- [ ] `RentalMandate` supports a list of co-owner signers (M2M to `PropertyOwnership` or a dedicated `MandateOwner` table).
- [ ] `build_mandate_signers` iterates all co-owners and inserts one signer record per owner before the agent.
- [ ] `RentalMandate.status` transitions to `active` only when all owner signers AND the agent have signed.
- [ ] If any owner signer rejects, the mandate transitions to a new `rejected` status and a notification is sent to the agent.
- [ ] Admin SPA `MandateTab.vue` shows all co-owner signer rows with individual status chips.

## Why I didn't fix it in the current task

Requires a data-model change (new M2M or through-table), additional migration, and changes to the
e-signing webhook handler — well beyond the M-effort scope of RNT-QUAL-005 and would risk destabilising
the working single-owner flow.
