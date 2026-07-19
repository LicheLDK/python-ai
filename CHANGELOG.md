# Changelog

All notable changes for AI SaaS Framework releases.

## [1.0.0] — 2026-07-19

### Added — Phases 0–12

- **Foundation:** FastAPI + Next.js + Postgres 16 + Redis 7 + Docker Compose; Alembic; health/ready
- **Auth:** JWT access (memory FE) + HttpOnly refresh cookie + CSRF; rate-limited login; RBAC
- **Users / Admin users:** profile + admin list/patch with audit
- **Documents:** multipart upload (jpeg/png/webp/pdf), ownership, local storage volume
- **OCR:** async ARQ jobs, OpenCV preprocess, PaddleOCR, results API, reconcile cron
- **AI:** OpenAI + Gemini adapters, prompts CRUD/activate, chat/vision/SSE, usage metering, rate limit
- **Pipelines:** document → preprocess → OCR → AI → persist with partial stage reporting
- **Statistics:** `stat_daily` materialize cron, daily/monthly/summary/CSV, Redis summary cache
- **Frontend:** auth shell, documents/OCR/AI/pipelines/dashboard, admin console (users/usage/OCR/audit/prompts/KPI)
- **Quality:** GitHub Actions CI, smoke scripts, OpenAPI coverage ≥95%, security/ops/backup/perf docs
- **Deployment:** staging Compose (`docker-compose.staging.yml`), deploy runbook, release gate record

### Notes

- Ollama adapter is stub-only (v1.1)
- RAG / S3 / soft multi-tenant deferred — see [BACKLOG_POST_V1.md](docs/BACKLOG_POST_V1.md)

### Tag instruction (T-12.04)

When ready to publish (do not force-push):

```powershell
git tag -a v1.0.0 -m "AI SaaS Framework v1.0.0"
git push origin v1.0.0
```
