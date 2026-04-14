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
NC='\033[0m' # no colour

ok()   { echo -e "  ${GREEN}✔${NC}  $1"; ((PASS++)); }
fail() { echo -e "  ${RED}✖${NC}  $1"; ((FAIL++)); }
info() { echo -e "  ${YELLOW}→${NC}  $1"; }

dc() {
  docker compose -f "$COMPOSE_FILE" "$@"
}

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Klikk Health Check — ${STACK}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── 1. All containers running ─────────────────────────────────────────────────
echo "[ 1 ] Container status"

EXPECTED_SERVICES="backend db gotenberg website_web admin_web agent_app_web caddy"

for service in $EXPECTED_SERVICES; do
  STATUS=$(dc ps --format "{{.Service}} {{.State}}" 2>/dev/null | grep "^${service} " | awk '{print $2}')
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
  HEALTH=$(dc ps --format "{{.Service}} {{.Health}}" 2>/dev/null | grep "^${service} " | awk '{print $2}')
  case "$HEALTH" in
    healthy)   ok "$service health check: healthy" ;;
    starting)  fail "$service health check: still starting (wait 30s and retry)" ;;
    unhealthy) fail "$service health check: UNHEALTHY" ;;
    "")        info "$service has no health check configured" ;;
    *)         info "$service health: $HEALTH" ;;
  esac
done

echo ""

# ── 3. Backend API ────────────────────────────────────────────────────────────
echo "[ 3 ] Backend API"

BACKEND_STATUS=$(dc exec -T backend wget -qO- --server-response http://localhost:8000/api/v1/health/ 2>&1 | grep "HTTP/" | awk '{print $2}')
if [ "$BACKEND_STATUS" = "200" ]; then
  ok "GET /api/v1/health/ → 200 OK"
else
  fail "GET /api/v1/health/ → ${BACKEND_STATUS:-no response}"
  info "Check logs: docker compose -f $COMPOSE_FILE logs --tail=30 backend"
fi

echo ""

# ── 4. Database connection ────────────────────────────────────────────────────
echo "[ 4 ] Database"

DB_READY=$(dc exec -T db pg_isready -U klikk_user -d klikk_db 2>&1)
if echo "$DB_READY" | grep -q "accepting connections"; then
  ok "PostgreSQL accepting connections"
else
  fail "PostgreSQL not ready: $DB_READY"
fi

# Check Django can reach the DB
DJANGO_DB=$(dc exec -T backend python manage.py shell -c "
from django.db import connection
connection.ensure_connection()
print('ok')
" 2>&1 | tail -1)
if [ "$DJANGO_DB" = "ok" ]; then
  ok "Django → database connection OK"
else
  fail "Django cannot reach database: $DJANGO_DB"
fi

echo ""

# ── 5. Pending migrations ─────────────────────────────────────────────────────
echo "[ 5 ] Migrations"

MIGRATE_CHECK=$(dc exec -T backend python manage.py migrate --check 2>&1)
if [ $? -eq 0 ]; then
  ok "No pending migrations"
else
  fail "Pending migrations detected — run: docker compose -f $COMPOSE_FILE exec backend python manage.py migrate"
  info "$MIGRATE_CHECK"
fi

echo ""

# ── 6. Gotenberg PDF service ──────────────────────────────────────────────────
echo "[ 6 ] Gotenberg"

GOTENBERG_STATUS=$(dc exec -T backend wget -qO- --server-response http://gotenberg:3000/health 2>&1 | grep "HTTP/" | awk '{print $2}')
if [ "$GOTENBERG_STATUS" = "200" ]; then
  ok "Gotenberg /health → 200 OK"
else
  fail "Gotenberg not responding (status: ${GOTENBERG_STATUS:-no response})"
fi

echo ""

# ── 7. Frontend services serving content ─────────────────────────────────────
echo "[ 7 ] Frontend services (nginx)"

for service in website_web admin_web agent_app_web; do
  HTTP_STATUS=$(dc exec -T $service wget -qO- --server-response http://localhost/ 2>&1 | grep "HTTP/" | awk '{print $2}')
  if [ "$HTTP_STATUS" = "200" ]; then
    ok "$service serving HTTP 200"
  else
    fail "$service not responding (status: ${HTTP_STATUS:-no response})"
  fi
done

echo ""

# ── 8. Caddy TLS proxy ────────────────────────────────────────────────────────
echo "[ 8 ] Caddy"

CADDY_STATUS=$(dc ps --format "{{.Service}} {{.State}}" 2>/dev/null | grep "^caddy " | awk '{print $2}')
if [ "$CADDY_STATUS" = "running" ]; then
  ok "Caddy is running"

  # Check Caddy admin API is alive
  CADDY_ADMIN=$(dc exec -T caddy wget -qO- http://localhost:2019/config/ 2>&1 | head -1)
  if echo "$CADDY_ADMIN" | grep -q "{"; then
    ok "Caddy admin API responding"
  else
    fail "Caddy admin API not responding"
  fi
else
  fail "Caddy is NOT running"
fi

echo ""

# ── 9. Django system check ────────────────────────────────────────────────────
echo "[ 9 ] Django system check"

DJANGO_CHECK=$(dc exec -T backend python manage.py check --deploy 2>&1)
CRITICAL=$(echo "$DJANGO_CHECK" | grep -c "CRITICAL\|ERROR" || true)
WARNINGS=$(echo "$DJANGO_CHECK" | grep -c "W[0-9]" || true)

if [ "$CRITICAL" -eq 0 ]; then
  ok "No critical Django errors"
else
  fail "$CRITICAL critical Django error(s) found"
  echo "$DJANGO_CHECK" | grep "CRITICAL\|ERROR"
fi

if [ "$WARNINGS" -gt 0 ]; then
  info "$WARNINGS Django warning(s) — run: docker compose -f $COMPOSE_FILE exec backend python manage.py check --deploy"
fi

echo ""

# ── Summary ───────────────────────────────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "$FAIL" -eq 0 ]; then
  echo -e "  ${GREEN}ALL $PASS CHECKS PASSED${NC}"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  exit 0
else
  echo -e "  ${RED}$FAIL CHECK(S) FAILED${NC} — $PASS passed"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  exit 1
fi
