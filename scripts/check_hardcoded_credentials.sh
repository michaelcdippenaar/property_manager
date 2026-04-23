#!/bin/bash
# Check for hardcoded credentials in login forms (RNT-SEC-045)
# Block commits with email/password patterns in LoginPage/login views

set -e

FAILED=0

# Search for hardcoded email patterns in login forms
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

if [ $FAILED -eq 1 ]; then
  exit 1
fi

exit 0
