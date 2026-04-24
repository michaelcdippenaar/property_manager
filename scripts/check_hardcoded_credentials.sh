#!/bin/bash
# Check for hardcoded credentials in login forms (RNT-SEC-045)
# Block commits with email/password patterns in LoginPage/login views.
#
# Extended in RNT-QUAL-054: also catches bare email literals assigned as JS/TS
# string values in .vue/.ts files, not inside an import.meta.env.DEV guard.

set -e

FAILED=0

# ── Check 1: login-form credential stubs ─────────────────────────────────── #
# Catches patterns like: ref('user@example.com') in login pages.
if grep -r 'ref(.*@.*\.com' \
    agent-app/src/pages \
    admin/src/views \
    tenant/src/views \
    2>/dev/null | grep -E '(LoginPage|login)' > /tmp/check_creds.txt 2>&1; then
  echo "ERROR: Found potential hardcoded credentials in login forms"
  cat /tmp/check_creds.txt
  FAILED=1
fi
rm -f /tmp/check_creds.txt

# ── Check 2: email literals assigned as JS/TS values in Vue/TS source ─────── #
# Only catches patterns where an email string is the right-hand side of an
# assignment or object property — e.g.:
#   email: 'someone@domain.com'
#   email: "someone@domain.com"
#   = 'someone@domain.com'
# This intentionally skips:
#   - placeholder="you@domain.com"   (HTML attribute values)
#   - href="mailto:..."              (HTML links)
#   - // comment or <!-- comment --> (commented-out code)
#   - Lines already using VITE_DEV_ or import.meta.env.DEV

BARE_EMAIL_MATCHES=$(grep -rn --include='*.vue' --include='*.ts' \
    -E "(email|Email)\s*[:=]\s*['\"][a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}['\"]" \
    admin/src agent-app/src web_app/src \
    2>/dev/null \
    | grep -v 'import.meta.env.DEV' \
    | grep -v 'VITE_DEV_' \
    | grep -v '\.spec\.' \
    | grep -v '__tests__' \
    | grep -v 'example\.com' \
    || true)

if [ -n "$BARE_EMAIL_MATCHES" ]; then
  echo "ERROR: Found hardcoded email literals assigned as JS/TS values in source files."
  echo "  Remove them or wrap in: import.meta.env.DEV && import.meta.env.VITE_DEV_EMAIL"
  echo "  Never ship real email addresses in production JS bundles."
  echo ""
  echo "$BARE_EMAIL_MATCHES"
  FAILED=1
fi

if [ $FAILED -eq 1 ]; then
  exit 1
fi

exit 0
