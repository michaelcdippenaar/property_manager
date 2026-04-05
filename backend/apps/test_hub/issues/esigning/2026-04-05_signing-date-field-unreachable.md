# Issue: Signing Date Field Not Displaying (Unreachable v-if Branch)
**Module:** esigning (frontend)
**Status:** FIXED
**Discovered:** 2026-04-05 (manual testing)

## Description
On the signing page, the date field next to the landlord signature only showed a "Pending" placeholder instead of displaying today's date. The date field was not fillable or auto-filled.

## Root Cause
In `SignatureBlockComponent.vue`, the v-if/v-else-if condition chain made the date display **unreachable**:

```html
<!-- 1. Shows signed image if mySignedData is truthy -->
<span v-if="isMyField && mySignedData">...</span>

<!-- 2. Shows click-to-sign if mySignedData is falsy -->
<button v-else-if="isMyField && !mySignedData">...</button>

<!-- 3. UNREACHABLE: conditions 1+2 already cover all isMyField cases -->
<span v-else-if="isMyField && node.attrs.fieldType === 'date'">...</span>
```

Since `PublicSignView.vue` auto-adds date fields to `signedFieldsMap` on page load (with empty `imageData`), `mySignedData` was always truthy for date fields. Condition #1 tried to render an `<img>` with empty `src`, showing a broken/invisible element.

## Fix Applied
Moved the date field check to **first** in the condition chain:

```html
<!-- 1. Date field: auto-filled (check BEFORE signed/unsigned) -->
<span v-if="isMyField && node.attrs.fieldType === 'date'">
  <Calendar /> {{ todayFormatted }}
</span>

<!-- 2. Already signed -->
<span v-else-if="isMyField && mySignedData">...</span>

<!-- 3. Unsigned -->
<button v-else-if="isMyField && !mySignedData">...</button>
```

## Files Changed
- `admin/src/extensions/SignatureBlockComponent.vue` — reordered v-if chain

## Status History
- 2026-04-05: Discovered during landlord signing test → date field shows placeholder
- 2026-04-05: Fixed v-if ordering → FIXED
