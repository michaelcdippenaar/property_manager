#!/usr/bin/env bash
# compile_email_templates.sh
# Compile base.mjml → compiled/base.html and re-apply Django template conditionals.
#
# Usage:
#   ./scripts/compile_email_templates.sh          # compile + patch
#   ./scripts/compile_email_templates.sh --check  # CI mode: exit non-zero if output is stale
#
# Requirements: Node.js + npx (mjml is pulled via npx, no global install needed)
# Python 3 is required for the post-processor.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TEMPLATES_DIR="$REPO_ROOT/backend/apps/notifications/email_templates"
MJML_SRC="$TEMPLATES_DIR/base.mjml"
COMPILED_OUT="$TEMPLATES_DIR/compiled/base.html"
PATCHER="$REPO_ROOT/scripts/patch_email_conditionals.py"
TEMP_MJML="$(mktemp /tmp/base_clean_XXXXXX.mjml)"
TEMP_HTML="$(mktemp /tmp/base_compiled_XXXXXX.html)"

CHECK_MODE=false
if [[ "${1:-}" == "--check" ]]; then
  CHECK_MODE=true
fi

cleanup() {
  rm -f "$TEMP_MJML" "$TEMP_HTML"
}
trap cleanup EXIT

# ── Step 1: strip Django {% if %} / {% endif %} wrapper lines from MJML ──────
# Only remove lines where {% if ... %} or {% endif %} is the SOLE content
# (these wrap entire <mj-button> / <mj-text> tags that MJML can't parse).
# Inline conditionals that appear alongside HTML content (e.g. unsubscribe link)
# are left intact — MJML passes text content through unchanged.
grep -vE '^\s*\{%-?\s*(if|endif)[^}]*%\}\s*$' "$MJML_SRC" > "$TEMP_MJML"

# ── Step 2: compile with MJML ─────────────────────────────────────────────────
echo "Compiling MJML → HTML …"
cd "$REPO_ROOT"
npx mjml "$TEMP_MJML" -o "$TEMP_HTML" --config.minify false

# ── Step 3: re-apply Django conditionals via Python post-processor ────────────
echo "Patching Django template conditionals …"
python3 "$PATCHER" "$TEMP_HTML" "$TEMP_HTML"

if $CHECK_MODE; then
  # ── CI / check mode: compare against committed output ─────────────────────
  if ! diff -q "$TEMP_HTML" "$COMPILED_OUT" > /dev/null 2>&1; then
    echo ""
    echo "FAIL: compiled/base.html is out of sync with base.mjml."
    echo "      Run ./scripts/compile_email_templates.sh and commit the result."
    diff "$TEMP_HTML" "$COMPILED_OUT" || true
    exit 1
  fi

  # Also assert conditional blocks are present (belt-and-braces)
  for pattern in "{% if cta_url %}" "{% if note %}" "{% if unsubscribe_url %}"; do
    if ! grep -qF "$pattern" "$COMPILED_OUT"; then
      echo "FAIL: '$pattern' is missing from compiled/base.html"
      exit 1
    fi
  done

  echo "PASS: compiled/base.html is up to date and contains all required conditional blocks."
else
  # ── Normal mode: write output ────────────────────────────────────────────
  mkdir -p "$(dirname "$COMPILED_OUT")"
  cp "$TEMP_HTML" "$COMPILED_OUT"
  echo "Written: $COMPILED_OUT"

  # Verify the conditionals are actually present
  for pattern in "{% if cta_url %}" "{% if note %}" "{% if unsubscribe_url %}"; do
    if ! grep -qF "$pattern" "$COMPILED_OUT"; then
      echo "ERROR: patch step failed — '$pattern' not found in output"
      exit 1
    fi
  done

  echo "All Django conditional blocks verified in compiled output."
fi
