# Changelog

All notable changes for AI SaaS Framework releases.

## [1.2.0] — 2026-07-19

### Added — Phase 17 (Erasure)

- **erasure_jobs** + ARQ `run_erasure_job`: hard-delete storage + documents (CASCADE), optional account anonymize
- **API:** `DELETE /users/me/data`, `GET /users/me/erasure-jobs/{id}`, admin `POST/GET /admin/erasure-jobs`
- **Policy:** audit logs retained; LLM provider logs out-of-band (local SoR only)

### Added — Phase 16 (Soft multi-tenant)

- **organizations** table + `users.org_id` (Alembic `0012`; default org backfill)
- **API:** `GET/PATCH /api/v1/orgs/me`, admin `GET/POST/PATCH /api/v1/admin/orgs`
- **Quota:** org AI rate limit overrides (Redis `aisaas:rl:ai:org:{org_id}`) alongside per-user limits
- **Branding:** JSONB bag on org (API-ready; UI deferred)

## [1.1.0] — 2026-07-19

### Added — Phase 15 (RAG)

- **EmbeddingPort:** OpenAI (`text-embedding-3-small`) + offline `hash` adapter
- **Store:** `document_chunks` (JSONB embeddings; no external vector DB)
- **API:** `POST /api/v1/rag/index`, `POST /api/v1/rag/search`
- **Chat citations:** `document_ids` / `top_k` on `/ai/chat` injects retrieved context

### Added — Phase 14 (S3 Storage)

- **S3StorageAdapter:** S3/MinIO via boto3 behind `StoragePort` (same key layout as local)
- **Factory:** `get_storage()` selects `local` | `s3` via `STORAGE_BACKEND` (default `local`)
- **Compose:** optional `minio` + `minio-init` profile; `S3_*` env contract

### Added — Phase 13 (Ollama)

- **OllamaAdapter:** local LLM via Ollama HTTP (`/api/chat`, `/api/tags`); chat + vision (llava)
- **Factory:** `ollama` in `SUPPORTED_PROVIDERS`; request `provider: "ollama"`
- **Schema:** Alembic `0010` adds `ollama` to `ai_provider` enum
- **Compose:** optional `ollama` profile + `OLLAMA_*` env contract

### Notes

- Default models: chat `llama3.2`, vision `llava` (pull before first use)
- Cost estimate for Ollama is `0` (local)

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
