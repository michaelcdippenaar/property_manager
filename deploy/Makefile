# Klikk DevOps Makefile
# Usage: make <target> [ARGS]
# Run from the repo root: make -f deploy/Makefile <target>
# Or cd into deploy/ and run: make <target>
#
# ROOT is resolved relative to this Makefile's location
ROOT := $(shell cd "$(dir $(lastword $(MAKEFILE_LIST)))/.." && pwd)

# Default environment for per-app builds
ENV ?= staging

# Default compose target for backend/utility commands (staging or production)
STACK ?= staging

.PHONY: help \
        dev-up dev-down dev-logs dev-restart \
        staging-build staging-up staging-down staging-logs staging-restart \
        prod-build prod-up prod-down prod-logs prod-restart \
        website-build admin-build agent-build \
        backend-migrate backend-createsuperuser backend-shell backend-logs \
        logs restart ps

# ─── Help ────────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "Klikk DevOps commands:"
	@echo ""
	@echo "  Development (local)"
	@echo "    dev-up                   Start all dev services"
	@echo "    dev-down                 Stop dev services"
	@echo "    dev-logs                 Tail all dev logs"
	@echo "    dev-restart              Restart dev services"
	@echo ""
	@echo "  Staging (Ubuntu home server)"
	@echo "    staging-build            Build all staging images (BUILD_MODE=staging)"
	@echo "    staging-up               Start all staging services (detached)"
	@echo "    staging-down             Stop staging services"
	@echo "    staging-logs             Tail all staging logs"
	@echo "    staging-restart          Rebuild and restart staging"
	@echo ""
	@echo "  Production (ISP VM)"
	@echo "    prod-build               Build all production images (BUILD_MODE=production)"
	@echo "    prod-up                  Start all production services (detached)"
	@echo "    prod-down                Stop production services"
	@echo "    prod-logs                Tail all production logs"
	@echo "    prod-restart             Rebuild and restart production"
	@echo ""
	@echo "  Per-app image builds"
	@echo "    website-build ENV=staging|production"
	@echo "    admin-build   ENV=staging|production"
	@echo "    agent-build   ENV=staging|production"
	@echo ""
	@echo "  Backend Django commands (STACK=staging|production)"
	@echo "    backend-migrate          Run pending migrations"
	@echo "    backend-createsuperuser  Create a Django superuser"
	@echo "    backend-shell            Open Django shell"
	@echo "    backend-logs             Tail backend logs"
	@echo ""
	@echo "  Utilities (STACK=staging|production, SERVICE=<name>)"
	@echo "    logs SERVICE=<name>      Tail logs for a specific service"
	@echo "    restart SERVICE=<name>   Restart a specific service"
	@echo "    ps                       List running containers"
	@echo ""

# ─── Development ─────────────────────────────────────────────────────────────
dev-up:
	docker compose -f $(ROOT)/docker-compose.yml up -d

dev-down:
	docker compose -f $(ROOT)/docker-compose.yml down

dev-logs:
	docker compose -f $(ROOT)/docker-compose.yml logs -f

dev-restart:
	docker compose -f $(ROOT)/docker-compose.yml restart

# ─── Staging ─────────────────────────────────────────────────────────────────
staging-build:
	docker compose -f $(ROOT)/deploy/docker-compose.staging.yml build

staging-up:
	docker compose -f $(ROOT)/deploy/docker-compose.staging.yml up -d

staging-down:
	docker compose -f $(ROOT)/deploy/docker-compose.staging.yml down

staging-logs:
	docker compose -f $(ROOT)/deploy/docker-compose.staging.yml logs -f

staging-restart: staging-build staging-up
	@echo "Staging rebuilt and restarted."

# ─── Production ──────────────────────────────────────────────────────────────
prod-build:
	docker compose -f $(ROOT)/deploy/docker-compose.prod.yml build

prod-up:
	docker compose -f $(ROOT)/deploy/docker-compose.prod.yml up -d

prod-down:
	docker compose -f $(ROOT)/deploy/docker-compose.prod.yml down

prod-logs:
	docker compose -f $(ROOT)/deploy/docker-compose.prod.yml logs -f

prod-restart: prod-build prod-up
	@echo "Production rebuilt and restarted."

# ─── Per-app builds ──────────────────────────────────────────────────────────
website-build:
	docker build \
	  --build-arg BUILD_MODE=$(ENV) \
	  -f $(ROOT)/website/Dockerfile \
	  -t klikk-website:$(ENV) \
	  $(ROOT)

admin-build:
	docker build \
	  --build-arg BUILD_MODE=$(ENV) \
	  -f $(ROOT)/admin/Dockerfile \
	  -t klikk-admin:$(ENV) \
	  $(ROOT)/admin

agent-build:
	docker build \
	  --build-arg BUILD_MODE=$(ENV) \
	  -f $(ROOT)/agent-app/Dockerfile \
	  -t klikk-agent:$(ENV) \
	  $(ROOT)/agent-app

# ─── Backend Django commands (target STACK=staging|production) ────────────────
_COMPOSE_FILE = $(ROOT)/deploy/docker-compose.$(STACK).yml

backend-migrate:
	docker compose -f $(_COMPOSE_FILE) exec backend python manage.py migrate

backend-createsuperuser:
	docker compose -f $(_COMPOSE_FILE) exec backend python manage.py createsuperuser

backend-shell:
	docker compose -f $(_COMPOSE_FILE) exec backend python manage.py shell

backend-logs:
	docker compose -f $(_COMPOSE_FILE) logs -f backend

# ─── Utilities ───────────────────────────────────────────────────────────────
SERVICE ?= backend

logs:
	docker compose -f $(_COMPOSE_FILE) logs -f $(SERVICE)

restart:
	docker compose -f $(_COMPOSE_FILE) restart $(SERVICE)

ps:
	docker compose -f $(_COMPOSE_FILE) ps
