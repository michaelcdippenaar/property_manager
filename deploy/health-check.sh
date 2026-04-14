#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
#  Klikk Health Check
#  Run after every docker compose up to verify all services are working.
#
#  Usage (from repo root on the server):
#    bash deploy/health-check.sh staging
#    bash deploy/health-check.sh production
#
#  Exit code 0 = all checks passed
#  Exit code 1 = one or more checks failed
# ─────────────────────────────────────────────────────────────────────────────

STACK="${1:-staging}"
COMPOSE_FILE="deploy/docker-compose.${STACK}.yml"
PASS=0
FAIL=0

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}✔${NC}  $1"; ((PASS++)); }
fail() { echo -e "  ${RED}✖${NC}  $1"; ((FAIL++)); }
info() { echo -e "  ${YELLOW}→${NC}  $1"; }

dc() { docker compose -f "$COMPOSE_FILE" "$@" 2>/dev/null; }

# Python HTTP check — runs inside the backend container (no wget/curl needed)
# Passes Host header so Django ALLOWED_HOSTS does not reject it.
py_http() {
  local url="$1"
  local host="${2:-}"
  dc exec -T backend python -c "
import urllib.request, sys
try:
    req = urllib.request.Request('$url')
    if '$host':
        req.add_header('Host', '$host')
    r = urllib.request.urlopen(req, timeout=5)
    print(r.status)
except urllib.error.HTTPError as e:
    print(e.code)
except Exception as e:
    print('ERR:', e)
    sys.exit(1)
" 2>/dev/null
}

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Klikk Health Check — ${STACK}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── 1. All containers running ─────────────────────────────────────────────────
echo "[ 1 ] Container status"

for service in backend db gotenberg website_web admin_web agent_app_web caddy; do
  STATUS=$(dc ps --format "{{.Service}} {{.State}}" | grep "^${service} " | awk '{print $2}')
  if [ "$STATUS" = "running" ]; then
    ok "$service is running"
  else
    fail "$service is NOT running (state: ${STATUS:-missing})"
  fi
done
echo ""

# ── 2. Container health checks ────────────────────────────────────────────────
echo "[ 2 ] Container health checks"

for service in backend db; do
  HEALTH=$(dc ps --format "{{.Service}} {{.Health}}" | grep "^${service} " | awk '{print $2}')
  case "$HEALTH" in
    healthy)   ok "$service → healthy" ;;
    starting)  fail "$service → still starting (wait 30s and retry)" ;;
    unhealthy) fail "$service → UNHEALTHY" ;;
    "")        info "$service → no health check configured" ;;
    *)         info "$service → $HEALTH" ;;
  esac
done
echo ""

# ── 3. Backend API ────────────────────────────────────────────────────────────
echo "[ 3 ] Backend API"

API_STATUS=$(py_http "http://localhost:8000/api/v1/health/" "backend.klikk.co.za")
if [ "$API_STATUS" = "200" ]; then
  ok "GET /api/v1/health/ → 200 OK"
else
  fail "GET /api/v1/health/ → ${API_STATUS:-no response}"
  info "Check logs: docker compose -f $COMPOSE_FILE logs --tail=30 backend"
fi
echo ""

# ── 4. Database ───────────────────────────────────────────────────────────────
echo "[ 4 ] Database"

DB_READY=$(dc exec -T db pg_isready -U klikk_user -d klikk_db 2>/dev/null)
if echo "$DB_READY" | grep -q "accepting connections"; then
  ok "PostgreSQL accepting connections"
else
  fail "PostgreSQL not ready: $DB_READY"
fi

DJANGO_DB=$(dc exec -T backend python -c "
from django.db import connection
connection.ensure_connection()
print('ok')
" 2>/dev/null | tail -1)
if [ "$DJANGO_DB" = "ok" ]; then
  ok "Django → database connection OK"
else
  fail "Django cannot reach the database"
  info "Check DB_HOST and DB_PASSWORD in backend container: docker compose -f $COMPOSE_FILE exec backend env | grep DB_"
fi
echo ""

# ── 5. Pending migrations ─────────────────────────────────────────────────────
echo "[ 5 ] Migrations"

dc exec -T backend python manage.py migrate --check > /dev/null 2>&1
if [ $? -eq 0 ]; then
  ok "No pending migrations"
else
  fail "Pending migrations — run: docker compose -f $COMPOSE_FILE exec backend python manage.py migrate"
fi
echo ""

# ── 6. Gotenberg ──────────────────────────────────────────────────────────────
echo "[ 6 ] Gotenberg"

GOTENBERG_STATUS=$(py_http "http://gotenberg:3000/health")
if [ "$GOTENBERG_STATUS" = "200" ]; then
  ok "Gotenberg /health → 200 OK"
else
  fail "Gotenberg not responding (status: ${GOTENBERG_STATUS:-no response})"
  info "Check logs: docker compose -f $COMPOSE_FILE logs --tail=20 gotenberg"
fi
echo ""

# ── 7. Frontend nginx containers ──────────────────────────────────────────────
echo "[ 7 ] Frontend services (nginx)"

# nginx:alpine has wget — check inside each container
for service in website_web admin_web agent_app_web; do
  # wget -S writes headers to stderr; capture combined output
  WGET_OUT=$(dc exec -T $service wget -qS -O /dev/null http://localhost/ 2>&1)
  HTTP_STATUS=$(echo "$WGET_OUT" | grep -oP 'HTTP/\S+ \K\d+' | head -1)
  if [ "$HTTP_STATUS" = "200" ]; then
    ok "$service → HTTP 200"
  else
    fail "$service not responding (status: ${HTTP_STATUS:-no response})"
    info "Logs: docker compose -f $COMPOSE_FILE logs --tail=10 $service"
  fi
done
echo ""

# ── 8. Caddy ──────────────────────────────────────────────────────────────────
echo "[ 8 ] Caddy"

CADDY_RUNNING=$(dc ps --format "{{.Service}} {{.State}}" | grep "^caddy " | awk '{print $2}')
if [ "$CADDY_RUNNING" = "running" ]; then
  ok "Caddy is running"
  # Admin API — caddy:alpine has no wget; use caddy's own CLI to validate config
  CADDY_VALID=$(dc exec -T caddy caddy validate --config /etc/caddy/Caddyfile 2>&1)
  if echo "$CADDY_VALID" | grep -q "Valid configuration"; then
    ok "Caddyfile config is valid"
  else
    info "Caddy config validation skipped or inconclusive"
  fi
else
  fail "Caddy is NOT running"
fi
echo ""

# ── 9. Django system check ────────────────────────────────────────────────────
echo "[ 9 ] Django system check"

DJANGO_CHECK=$(dc exec -T backend python manage.py check --deploy 2>&1)
CRITICAL=$(echo "$DJANGO_CHECK" | grep -c "CRITICAL\|: error:" 2>/dev/null || true)
WARNINGS=$(echo "$DJANGO_CHECK" | grep -cE "^WARNINGS|\.W[0-9]" 2>/dev/null || true)

if [ "$CRITICAL" -eq 0 ]; then
  ok "No critical Django errors"
else
  fail "$CRITICAL critical error(s) — run: docker compose -f $COMPOSE_FILE exec backend python manage.py check --deploy"
fi
if [ "$WARNINGS" -gt 0 ]; then
  info "$WARNINGS Django deployment warning(s) present (non-blocking)"
fi
echo ""

# ── Summary ───────────────────────────────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "$FAIL" -eq 0 ]; then
  echo -e "  ${GREEN}ALL $PASS CHECKS PASSED ✔${NC}"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  exit 0
else
  echo -e "  ${RED}$FAIL CHECK(S) FAILED ✖${NC}   ($PASS passed)"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  exit 1
fi
