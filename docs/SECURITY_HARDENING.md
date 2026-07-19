# Security Hardening Notes (T-11.05)

Checklist applied for v1. Re-verify before staging/production.

## CORS

- Env: `CORS_ORIGINS` (comma-separated allowlist) — **no `*` with credentials**
- Compose/local default: `http://localhost:3000`
- FastAPI: `allow_credentials=True`, methods/headers `*`
- [x] Production must set explicit web origins only

## Cookies / CSRF (ADR-008 / ADR-029)

| Cookie | HttpOnly | Secure | SameSite | Path |
| --- | --- | --- | --- | --- |
| `refresh_token` | yes | yes when `APP_ENV` ∉ {local,test,dev,development} | Lax | `/api/v1/auth` |
| `csrf_token` | no (readable) | same as above | Lax | `/api/v1/auth` |

- Refresh/logout require double-submit: cookie `csrf_token` == header `X-CSRF-Token`
- Access JWT: **memory only** on FE (`frontend/lib/auth.ts`) — never localStorage
- [x] Staging/production: serve API+web over HTTPS so `Secure` cookies stick

## Secrets

- Do **not** commit `.env` (only `.env.example` / `.env.staging.example`)
- Rotate `JWT_SECRET` per environment; min 32 random bytes recommended
- Provider keys (`OPENAI_API_KEY`, `GEMINI_API_KEY`) via env/secret store only
- Guidance: enable GitHub secret scanning; optionally run `gitleaks detect --source .`

## Headers / transport

- Prefer reverse proxy TLS termination in staging+
- Do not expose Postgres / Redis ports publicly in staging overlays
- Rate limits: see [OPS_DEFAULTS.md](OPS_DEFAULTS.md)

## Authz

- Admin routes use `AdminUser` dependency — non-admin → 403 envelope
- Document/OCR/pipeline ownership checks in services

## Sign-off

| Item | Reviewer | Date | OK |
| --- | --- | --- | --- |
| CORS allowlist | | | |
| Cookie flags | | | |
| Secret hygiene | | | |
| Admin 403 | | | |
