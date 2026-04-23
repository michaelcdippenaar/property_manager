#!/usr/bin/env bash
# RNT-SEC-042 — PII masking drift guard
#
# Scans admin/src/**/*.vue for bare v-model bindings on canonical PII field names
# that are NOT protected by <MaskedInput> or data-clarity-mask.
#
# A violation looks like:
#   <input v-model="something.id_number" ...>          ← bare input, missing masking
#
# A passing line looks like:
#   <MaskedInput v-model="something.id_number" ...>    ← wrapper in place
#   h('input', { 'data-clarity-mask': 'true', ...})    ← render fn with mask
#
# Exit codes:
#   0 — all PII fields are masked
#   1 — one or more violations found
#
# Usage (from repo root):
#   bash admin/scripts/check-pii-masking.sh
#
# Usage (from admin/):
#   bash scripts/check-pii-masking.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SRC_DIR="${REPO_ROOT}/admin/src"

# Canonical PII field names (must match piiFields.ts)
PII_FIELDS=(
  id_number
  account_number
  branch_code
  trust_account_number
  trust_branch_code
  representative_id_number
  passport
)

VIOLATIONS=0

for field in "${PII_FIELDS[@]}"; do
  # Match lines that have v-model="....<field>" (or v-model='....<field>')
  # but are on a bare <input (not <MaskedInput) and do NOT have data-clarity-mask.
  #
  # Strategy: grep for the pattern, then filter out known-safe patterns.
  matches=$(grep -rn \
    --include="*.vue" \
    "v-model=['\"].*\b${field}\b['\"]" \
    "${SRC_DIR}" \
    | grep -v 'MaskedInput' \
    | grep -v "data-clarity-mask" \
    | grep -v "data-clarity-mask='true'" \
    | grep --extended-regexp '<input[^>]+v-model' \
    || true)

  if [[ -n "${matches}" ]]; then
    echo ""
    echo "FAIL: bare <input> with v-model on PII field '${field}' (missing <MaskedInput> wrapper or data-clarity-mask):"
    echo "${matches}" | sed 's/^/  /'
    VIOLATIONS=$((VIOLATIONS + 1))
  fi
done

if [[ "${VIOLATIONS}" -eq 0 ]]; then
  echo "PASS: all PII fields are masked (checked: ${PII_FIELDS[*]})"
  exit 0
else
  echo ""
  echo "FAIL: ${VIOLATIONS} PII field(s) found without masking."
  echo "  Fix: replace <input v-model=\"...\"> with <MaskedInput v-model=\"...\"> for PII fields."
  echo "  See: admin/src/components/shared/MaskedInput.vue"
  exit 1
fi
