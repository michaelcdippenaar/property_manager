# Web app (`web_app/`) runtime — 2026-03-25

## Summary

The tenant **Vue** app in [`web_app/`](../../web_app/) is **not** started by the repo’s [`docker-compose.yml`](../../docker-compose.yml). Compose runs `db`, `backend`, and **`admin`** (port **5173**) only.

## Local development

- **URL:** `http://localhost:5174` (fixed in [`web_app/vite.config.ts`](../../web_app/vite.config.ts) via `server.port` and `strictPort: true`).
- **Command:** `cd web_app && npm run dev`
- **API:** `VITE_API_URL` defaults to `http://localhost:8000/api/v1` (see [`web_app/.env.example`](../../web_app/.env.example)).

Project overview and the same run instructions are in [`CONTEXT.md`](../../CONTEXT.md).

## CORS

[`backend/config/settings/base.py`](../../backend/config/settings/base.py) includes `http://localhost:5174` and `http://127.0.0.1:5174` in `CORS_ALLOWED_ORIGINS` alongside the admin origin (5173). Local settings may still use `CORS_ALLOW_ALL_ORIGINS` when developing.

## Why two Vite ports

- **5173** — staff **admin** SPA ([`admin/vite.config.ts`](../../admin/vite.config.ts)).
- **5174** — **tenant** web companion (`web_app/`), so both can run simultaneously without port clashes.
