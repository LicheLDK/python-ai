## Summary

<!-- What changed and why (link PRD/SDS/TASKS IDs). -->

## Spec links

- [ ] PRD section:
- [ ] SDS section:
- [ ] TASKS ID(s):

## Layer checklist (SDS §4 / ADR-003) — T-11.04

- [ ] Controllers (`routers/`) have no business logic / SQL / provider SDKs
- [ ] Services do not depend on FastAPI `Request`/`Response` (HTTP details)
- [ ] Repositories do not call AI/OCR/HTTP adapters
- [ ] Adapters isolate vendor SDKs behind ports
- [ ] Workers call services/adapters — not routers
- [ ] Frontend pages call only `frontend/services/*` (no raw fetch sprawl)
- [ ] Schema changes via Alembic (no manual prod DDL)
- [ ] Error responses use standard envelope (`code`, `message`, `request_id`)

## Security checklist (T-11.05)

- [ ] No secrets in diff (`.env`, keys, dumps)
- [ ] CORS / cookie / CSRF implications considered
- [ ] Admin routes remain admin-gated

## Test plan

- [ ] Unit / API tests added or updated
- [ ] `docker compose` smoke (`scripts/smoke.sh`) if auth/upload touched
- [ ] Frontend `npm run lint` / `npm run build` if FE changed

## Docs

- [ ] `usage.md` updated when behavior/ops steps change
- [ ] TASKS status marked when completing a task ID
