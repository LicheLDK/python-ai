# TASKS.md — Implementation Task Breakdown

| Field | Value |
| --- | --- |
| **Product** | AI SaaS Framework |
| **Version** | 1.0.0 |
| **Status** | Ready for Implementation |
| **Parent Docs** | [PRD.md](./PRD.md) v1.0.0, [SDS.md](./SDS.md) v1.0.0 |
| **Last Updated** | 2026-07-18 |
| **Code** | This document does **not** include source code |

---

## 1. How to Use This Document

### 1.1 Task Attributes

| Attribute | Meaning |
| --- | --- |
| **ID** | Stable task identifier (`T-{PHASE}.{NN}`) |
| **Priority** | `High` / `Medium` / `Low` |
| **Depends on** | Tasks that must be **Done** before this task starts |
| **Blocks** | Tasks waiting on this one (informational) |
| **Deliverable** | Concrete, reviewable outcome (no code in this doc) |
| **Exit criteria** | When the task may be marked Done |

### 1.2 Priority Definitions

| Priority | Rule |
| --- | --- |
| **High** | v1 Must (PRD P0). Blocks core journey or release gate |
| **Medium** | v1 Should (PRD P1). Important but not on critical path for first vertical slice |
| **Low** | v1 Could / polish / deferred-friendly (PRD P2 or post-slice) |

### 1.3 Independence Rule

Each task is sized so one engineer can complete it with a single PR-sized scope, given its dependencies are Done. Tasks do **not** require another in-progress task’s unfinished work.

### 1.4 Phase Order (Infrastructure → Deployment)

```
0 Foundation
→ 1 Authentication
→ 2 Users & RBAC
→ 3 Documents & Storage
→ 4 OCR & Workers
→ 5 AI Providers & Prompts
→ 6 Pipelines
→ 7 Statistics
→ 8 Frontend Shell & Auth UI
→ 9 Frontend Feature Consoles
→ 10 Admin UI & Dashboard
→ 11 Quality, CI & Hardening
→ 12 Deployment & Release
```

### 1.5 Status Legend (for tracking)

Use in project board / PR titles: `Todo` · `In Progress` · `Blocked` · `Done` · `Cancelled`

---

## 2. Dependency Overview (Critical Path)

```
T-0.01 → T-0.02 → T-0.03 → T-0.04 → T-0.05 → T-0.06 → T-0.07
                                                         ↓
                              T-1.01 → T-1.02 → T-1.03 → T-1.04 → T-1.05
                                                         ↓
                                              T-2.01 → T-2.02 → T-2.03
                                                         ↓
                              T-3.01 → T-3.02 → T-3.03
                                         ↓
                              T-4.01 → T-4.02 → T-4.03 → T-4.04
                                         ↓
                              T-5.01 → T-5.02 → T-5.03 → T-5.04 → T-5.05
                                         ↓
                                      T-6.01 → T-6.02
                                         ↓
                                      T-7.01 → T-7.02 → T-7.03
                                         ↓
              T-8.* (can start after T-1.05 for auth UI; features after matching APIs)
              T-9.* → T-10.* → T-11.* → T-12.*
```

**Parallelism tips**

- After `T-0.07`, backend Auth (`T-1.*`) and Frontend shell scaffolding (`T-8.01`) can proceed in parallel once API base URL contract exists.
- After Auth, Documents (`T-3.*`) and Admin user API (`T-2.03`) can proceed in parallel.
- OpenAI adapter (`T-5.02`) and Gemini adapter (`T-5.03`) are parallel after `T-5.01`.
- Frontend feature pages (`T-9.*`) start only when the matching API task is Done.

---

## Phase 0 — Foundation (Infrastructure)

**Goal:** Compose stack boots; empty layered backend/frontend skeletons; health/ready; config; DB/Redis wiring; Alembic ready.  
**Phase exit:** `docker compose up` → `/health` OK, `/ready` OK (Postgres + Redis).

| ID | Task | Priority | Depends on | Deliverable | Exit criteria |
| --- | --- | --- | --- | --- | --- |
| **T-0.01** ✅ Done | Create repository layout per SDS §5 (folders only, no domain logic) | High | — | Directory tree matches SDS; placeholder package markers | Layout review approved against SDS |
| **T-0.02** ✅ Done | Define environment contract (`.env.example`) per SDS §6.6 | High | T-0.01 | Documented env keys with descriptions; no secrets | Keys cover DATABASE, REDIS, JWT, AI, STORAGE, CORS, APP_ENV |
| **T-0.03** ✅ Done | Docker Compose services: `postgres`, `redis`, volumes, networks | High | T-0.02 | Compose file with healthy Postgres 16+ and Redis 7+ | Both services healthy via Compose healthchecks |
| **T-0.04** ✅ Done | Backend Docker image + API process entry (FastAPI app factory shell) | High | T-0.03 | `api` service builds and starts | Container listens; responds to probe path once wired |
| **T-0.05** ✅ Done | Core settings, logging, request-id middleware, error envelope | High | T-0.04 | Settings load from env; JSON logs; `X-Request-ID`; standard error body | Manual call returns envelope + request_id |
| **T-0.06** ✅ Done | PostgreSQL engine/session + Alembic bootstrap (empty migration chain) | High | T-0.05 | DB connectivity; `alembic upgrade head` succeeds (baseline) | API can obtain a DB session |
| **T-0.07** ✅ Done | Redis client + Health/Ready endpoints | High | T-0.06 | `/health` liveness; `/ready` checks Postgres + Redis | Ready returns 200 when deps up, 503 when down |
| **T-0.08** ✅ Done | Backend Dockerfile entrypoint wait-for-deps script | Medium | T-0.07 | Entrypoint waits for Postgres/Redis before boot | Cold start does not crash-loop on race |
| **T-0.09** ✅ Done | Frontend Docker skeleton (Next.js app shell, no feature pages) | Medium | T-0.03 | `web` service builds; placeholder page | Compose includes `web` |
| **T-0.10** ✅ Done | Root README: architecture summary, compose up, doc links | Medium | T-0.07, T-0.09 | README usable by new developer | Time-to-first-health ≤ 30 min on clean machine (manual check) |
| **T-0.11** ✅ Done | Scripts stubs: migrate / seed / smoke (documented behavior) | Low | T-0.07 | Script entrypoints documented in README | Smoke checks health/ready only |

**Phase 0 dependency notes**

- `T-0.09` does not need backend Ready; only Compose network.
- Critical path: `T-0.01` → … → `T-0.07`.

---

## Phase 1 — Authentication

**Goal:** Register, login, JWT access, refresh rotation (HttpOnly cookie), logout, CSRF, rate limit.  
**Phase exit:** Auth E2E via Swagger/HTTP; inactive user blocked.

| ID | Task | Priority | Depends on | Deliverable | Exit criteria |
| --- | --- | --- | --- | --- | --- |
| **T-1.01** ✅ Done | Alembic migration: `users`, `refresh_tokens` | High | T-0.07 | Tables + indexes per SDS §10.4, §10.7 | Migration upgrade/downgrade works |
| **T-1.02** ✅ Done | Security primitives: password hashing (Argon2id), JWT issue/verify | High | T-1.01 | Core security module; unit-testable without HTTP | Hash verify + JWT claim round-trip |
| **T-1.03** ✅ Done | Auth repositories + AuthService (register/login/refresh/logout/reuse detection) | High | T-1.02 | Service layer; Redis rate limit + denylist keys per SDS | Service tests cover success/fail/reuse |
| **T-1.04** ✅ Done | Auth routers + schemas: register, login, refresh, logout, csrf | High | T-1.03 | `/api/v1/auth/*` per SDS §9.2; OpenAPI visible | Swagger flow: register→login→refresh→logout |
| **T-1.05** ✅ Done | Auth dependencies: `current_user`, role guard hooks | High | T-1.04 | FastAPI Depends for Bearer user + role checks | Protected stub route returns 401/403 correctly |
| **T-1.06** ✅ Done | Auth API tests (login rate limit, inactive user, CSRF failure) | High | T-1.05 | API test suite for auth | CI-ready tests green |
| **T-1.07** ✅ Done | Seed script: default admin user (env-driven credentials) | Medium | T-1.03 | Documented admin seed | Admin can log in after seed |
| **T-1.08** | Access-token jti denylist on logout (optional hardening) | Low | T-1.05 | Documented behavior; Redis deny for access jti | Logged-out access rejected until expiry |

---

## Phase 2 — Users & RBAC

**Goal:** Profile APIs; admin user management; permissions schema ready.  
**Phase exit:** User can read/patch self; admin can list/patch users; non-admin gets 403 on admin routes.

| ID | Task | Priority | Depends on | Deliverable | Exit criteria |
| --- | --- | --- | --- | --- | --- |
| **T-2.01** ✅ Done | Alembic: `permissions`, `role_permissions` + seed permission codes | Medium | T-1.01 | Schema per SDS §10.5–10.6; seed rows | Migration + seed idempotent |
| **T-2.02** ✅ Done | User module: `GET/PATCH /api/v1/users/me` | High | T-1.05 | User service/repo/router/schemas | Owner-only update; email immutable |
| **T-2.03** ✅ Done | Admin users API: list/get/patch (+ audit write hook) | High | T-2.02, T-2.04 | `/api/v1/admin/users*` per SDS §9.9 | Admin OK; user role → 403 |
| **T-2.04** ✅ Done | AuditLog model/migration + AuditService (write API for mutations) | High | T-1.01 | `audit_logs` table; service method | Admin user patch creates audit row |
| **T-2.05** | Permission enforcement helpers (P1 wiring; role still primary in v1) | Low | T-2.01, T-1.05 | Optional permission check utility | Documented; not required on all routes yet |
| **T-2.06** ✅ Done | Users/Admin API tests | High | T-2.03 | Tests for RBAC matrix | Green |

**Note:** `T-2.03` depends on `T-2.04` for audit side effects; if audit is split, implement audit stub first then enrich.

---

## Phase 3 — Documents & Storage

**Goal:** Upload images/PDF; metadata; local storage port; ownership.  
**Phase exit:** Authenticated user uploads and lists documents.

| ID | Task | Priority | Depends on | Deliverable | Exit criteria |
| --- | --- | --- | --- | --- | --- |
| **T-3.01** ✅ Done | Alembic: `documents` table | High | T-1.01 | SDS §10.8 | Migration OK |
| **T-3.02** ✅ Done | `StoragePort` + LocalStorageAdapter + volume mount in Compose | High | T-0.04, T-3.01 | Files land under `STORAGE_PATH` layout SDS §10.20 | File exists on disk after upload service call |
| **T-3.03** ✅ Done | DocumentService + routers: POST/GET list/GET id/DELETE | High | T-3.02, T-1.05 | `/api/v1/documents*` SDS §9.4 | MIME/size rejection; owner isolation |
| **T-3.04** ✅ Done | Document API tests (415/413/404/ownership) | High | T-3.03 | Test suite | Green |
| **T-3.05** | Idempotency-Key support for document POST (Redis) | Medium | T-3.03, T-0.07 | Duplicate key returns same document | Replay within TTL safe |
| **T-3.06** | Word/Excel/Text ingest hooks (interfaces + stubs only) | Low | T-3.03 | Extension points documented | No production parsers required |

---

## Phase 4 — OCR & Workers

**Goal:** Async OCR jobs via ARQ; OpenCV preprocess; PaddleOCR; results; history API.  
**Phase exit:** Upload → create job → worker succeeds → results readable.

| ID | Task | Priority | Depends on | Deliverable | Exit criteria |
| --- | --- | --- | --- | --- | --- |
| **T-4.01** ✅ Done | Alembic: `ocr_jobs`, `ocr_results` | High | T-3.01 | SDS §10.9–10.10 | Migration OK |
| **T-4.02** ✅ Done | Worker service in Compose (ARQ) + queue publisher adapter | High | T-0.07, T-0.04 | `worker` container consumes Redis queue | Enqueued no-op job runs |
| **T-4.03** ✅ Done | ImagePreprocessPort + OpenCV adapter | High | T-4.02 | Preprocess options deskew/denoise/contrast | Unit test on sample fixture image |
| **T-4.04** ✅ Done | OcrEnginePort + PaddleOCR adapter (lang `korean+en`) | High | T-4.03 | Text + boxes extraction | Fixture image yields non-empty text |
| **T-4.05** ✅ Done | OCR job worker handler + OcrService/routers (create/list/get/results) | High | T-4.01, T-4.04, T-3.03 | `/api/v1/ocr/*` SDS §9.5; status lifecycle | E2E poll until `succeeded` |
| **T-4.06** ✅ Done | OCR retry/backoff + failure persistence | Medium | T-4.05 | attempt_count; failed status + error | Forced failure recorded |
| **T-4.07** ✅ Done | OCR page limit / PDF page split behavior | Medium | T-4.05 | `OCR_MAX_PAGES` enforced | Over-limit → 422 or failed job with clear error |
| **T-4.08** ✅ Done | OCR API + worker integration tests | High | T-4.05 | Tests with mocked engine and one real-ish fixture path | Green |
| **T-4.09** ✅ Done | Queued-job reconciler (Redis loss recovery) | Low | T-4.05 | Periodic scan of `queued`/`running` stale jobs | Documented ops behavior |

---

## Phase 5 — AI Providers & Prompts

**Goal:** Provider port; OpenAI + Gemini; prompts; chat/vision; usage metering; config switch.  
**Phase exit:** Config-only primary provider switch; usage rows persisted.

| ID | Task | Priority | Depends on | Deliverable | Exit criteria |
| --- | --- | --- | --- | --- | --- |
| **T-5.01** ✅ Done | Alembic: `ai_prompts`, `ai_requests`, `ai_usages` | High | T-1.01 | SDS §10.11–10.13 | Migration OK |
| **T-5.02** ✅ Done | `LlmProviderPort` + OpenAI adapter | High | T-5.01, T-0.05 | chat + vision methods; error mapping | Contract tests with mocked HTTP |
| **T-5.03** ✅ Done | Gemini adapter (same port) | High | T-5.01, T-0.05 | chat + vision parity | Contract tests with mocked HTTP |
| **T-5.04** ✅ Done | LLM factory (primary/fallback flags) | High | T-5.02, T-5.03 | Selection via env; optional fallback | Switching providers needs zero code change |
| **T-5.05** ✅ Done | PromptService + CRUD/activate admin APIs | High | T-5.01, T-1.05, T-2.03 | `/api/v1/ai/prompts*` SDS §9.6 | Versioning + one active per name |
| **T-5.06** ✅ Done | AiService + `POST /ai/chat`, `POST /ai/vision` + usage write | High | T-5.04, T-5.05, T-3.03 | SDS §9.6 chat/vision | Usage row per request; OpenAPI complete |
| **T-5.07** ✅ Done | AI rate limiting / per-user quota hooks | Medium | T-5.06, T-0.07 | Redis counters; 429 mapping | Exceeded quota returns 429 |
| **T-5.08** ✅ Done | Streaming chat (SSE) | Medium | T-5.06 | Streaming endpoint or flag | Documented client consumption |
| **T-5.09** ✅ Done | Prompt seed pack (OCR-analysis defaults) | Medium | T-5.05 | Seed prompts for pipeline later | Seeds idempotent |
| **T-5.10** ✅ Done | Ollama adapter stub (interface only) | Low | T-5.01 | Port reserved; not wired in factory | Docs mark v1.1 |
| **T-5.11** ✅ Done | AI API tests (provider mock, prompt resolve, authz on prompt write) | High | T-5.06 | Test suite | Green |

---

## Phase 6 — Pipelines

**Goal:** Document → preprocess → OCR → AI → persist orchestration.  
**Phase exit:** Single pipeline run reaches `succeeded` with stage JSON.

| ID | Task | Priority | Depends on | Deliverable | Exit criteria |
| --- | --- | --- | --- | --- | --- |
| **T-6.01** ✅ Done | Alembic: `pipeline_runs` | High | T-4.01, T-5.01 | SDS §10.14 | Migration OK |
| **T-6.02** ✅ Done | PipelineService + worker job + routers | High | T-6.01, T-4.05, T-5.06 | `/api/v1/pipelines/*` SDS §9.7 | Stages recorded; poll works |
| **T-6.03** ✅ Done | Pipeline failure partial-stage reporting | Medium | T-6.02 | Failed stage leaves prior outputs referenced | Client sees which stage failed |
| **T-6.04** ✅ Done | Pipeline API/worker tests | High | T-6.02 | Tests with mocks | Green |

---

## Phase 7 — Statistics

**Goal:** Daily materialization; monthly rollup; summary APIs.  
**Phase exit:** Stats endpoints return chart-ready series for self/admin scopes.

| ID | Task | Priority | Depends on | Deliverable | Exit criteria |
| --- | --- | --- | --- | --- | --- |
| **T-7.01** ✅ Done | Alembic: `stat_daily` | High | T-0.06 | SDS §10.16 | Migration OK |
| **T-7.02** ✅ Done | Stats materialize worker (from OCR/AI/pipeline events or periodic job) | High | T-7.01, T-4.05, T-5.06 | Upsert metrics names per SDS §9.8 | Daily rows appear after activity |
| **T-7.03** ✅ Done | Stats routers: daily, monthly, summary (+ scope authz) | High | T-7.02, T-1.05 | `/api/v1/stats/*` | User sees self; admin can request global |
| **T-7.04** ✅ Done | Stats CSV export | Medium | T-7.03 | `/api/v1/stats/export` P1 | CSV downloads for range |
| **T-7.05** ✅ Done | Optional Redis cache for summary | Low | T-7.03 | Short TTL cache keys | Cache miss still correct |
| **T-7.06** ✅ Done | Stats API tests | High | T-7.03 | Test suite | Green |

---

## Phase 8 — Frontend Shell & Auth UI

**Goal:** Next.js App Router shell; HTTP client; auth pages; guards.  
**Phase exit:** Browser login/refresh/logout against real API.

| ID | Task | Priority | Depends on | Deliverable | Exit criteria |
| --- | --- | --- | --- | --- | --- |
| **T-8.01** ✅ Done | Frontend app structure: route groups `(auth)/(app)/(admin)`, layout, nav shell | High | T-0.09 | SDS §5.19–5.20 skeleton pages | Routes render placeholders |
| **T-8.02** ✅ Done | `frontend/services/http` + auth token memory + refresh intercept + CSRF | High | T-8.01, T-1.04 | Typed base client | 401 triggers refresh once |
| **T-8.03** ✅ Done | Auth UI: login, register, logout; auth service client | High | T-8.02 | Working auth pages | Manual E2E login OK |
| **T-8.04** ✅ Done | Route guards (authenticated / admin-only) | High | T-8.03, T-1.05 | Unauthorized redirected; admin gated | Non-admin cannot open `/admin` |
| **T-8.05** ✅ Done | Shared UI primitives (button, input, table, modal) | Medium | T-8.01 | Reusable components folder | Used by auth forms |
| **T-8.06** ✅ Done | Frontend env: `NEXT_PUBLIC_API_BASE_URL` documented | High | T-0.02, T-8.02 | Compose/web env wired | Web calls correct API origin |
| **T-8.07** ✅ Done | Basic FE lint/format setup | Low | T-8.01 | Lint scripts documented | Lint runs clean on shell |

---

## Phase 9 — Frontend Feature Consoles

**Goal:** User-facing documents, OCR, AI, pipelines, personal dashboard wired to APIs.  
**Phase exit:** Core AI-first journey operable from UI.

| ID | Task | Priority | Depends on | Deliverable | Exit criteria |
| --- | --- | --- | --- | --- | --- |
| **T-9.01** ✅ Done | Documents UI + `services/documents` | High | T-8.04, T-3.03 | Upload/list/detail | Upload appears in list |
| **T-9.02** ✅ Done | OCR console + polling + `services/ocr` | High | T-9.01, T-4.05 | Job create/status/results view | Poll reaches succeeded |
| **T-9.03** ✅ Done | AI chat/vision UI + `services/ai` | High | T-8.04, T-5.06 | Chat panel; vision from document/OCR | Response + usage shown |
| **T-9.04** ✅ Done | Pipelines UI + polling + `services/pipelines` | High | T-9.01, T-6.02 | Run create/status stages | Succeeded run visible |
| **T-9.05** ✅ Done | User dashboard page (summary cards + recent jobs) | High | T-8.04, T-7.03 | Dashboard consumes summary/stats | Numbers match API |
| **T-9.06** ✅ Done | Charts for personal daily stats | Medium | T-9.05, T-7.03 | Chart components | Renders series |
| **T-9.07** ✅ Done | Prompt browser (read-only for users) | Low | T-9.03, T-5.05 | List active prompts | Read OK |
| **T-9.08** ✅ Done | UX empty/error/loading states polish | Low | T-9.02, T-9.03, T-9.04 | Consistent states | Review pass |

---

## Phase 10 — Admin UI & Operational Dashboard

**Goal:** Admin console for users, usage, OCR history, audit, global KPI.  
**Phase exit:** Admin acceptance checklist from PRD §20.3 items 5–7 via UI.

| ID | Task | Priority | Depends on | Deliverable | Exit criteria |
| --- | --- | --- | --- | --- | --- |
| **T-10.01** ✅ Done | Admin API: usage, ocr-history, audit-logs, dashboard aggregate | High | T-2.03, T-4.05, T-5.06, T-2.04, T-7.03 | `/api/v1/admin/usage`, `ocr-history`, `audit-logs`, `dashboard` | Swagger + RBAC 403 for non-admin |
| **T-10.02** ✅ Done | Admin users UI | High | T-8.04, T-2.03 | List/search/activate/role | Changes reflect via API |
| **T-10.03** ✅ Done | Admin AI usage UI | High | T-10.01, T-8.04 | Filters + table | Rows match DB |
| **T-10.04** ✅ Done | Admin OCR history UI | High | T-10.01 | Job list + result drill-down | Succeeded job shows text |
| **T-10.05** ✅ Done | Admin audit log UI | Medium | T-10.01 | Filterable table | Admin patch appears |
| **T-10.06** ✅ Done | Admin dashboard KPI UI | High | T-10.01 | Global charts/KPIs | Matches `/admin/dashboard` |
| **T-10.07** ✅ Done | Admin prompt management UI | Medium | T-5.05, T-8.04 | Create/version/activate | Active prompt usable in AI UI |
| **T-10.08** ✅ Done | Admin UI access regression tests (manual checklist doc) | Medium | T-10.02–T-10.06 | Written QA checklist | Checklist signed |

---

## Phase 11 — Quality, CI & Hardening

**Goal:** Automated quality gates; security/ops hardening; layer rules enforced in process.  
**Phase exit:** CI green on main path; production checklist draft complete.

| ID | Task | Priority | Depends on | Deliverable | Exit criteria |
| --- | --- | --- | --- | --- | --- |
| **T-11.01** ✅ Done | GitHub Actions CI: lint + backend tests + frontend build | High | T-1.06, T-8.01 | Workflow file | PR CI required checks |
| **T-11.02** ✅ Done | Compose smoke job: health → register/login → (optional) upload | High | T-3.03, T-1.04 | Smoke script in CI or docs | Smoke passes on Compose |
| **T-11.03** ✅ Done | OpenAPI coverage review vs SDS §9 (≥95%) | High | T-10.01, T-6.02, T-7.03 | Gap list closed | Coverage met |
| **T-11.04** ✅ Done | Architecture review checklist in PR template (layer rules) | High | T-0.01 | PR template + docs link | Template used |
| **T-11.05** ✅ Done | Security hardening pass: CORS, cookie flags, secret scan guidance | High | T-1.04, T-8.02 | Hardening notes applied | Checklist items checked |
| **T-11.06** ✅ Done | Rate-limit tuning defaults documented | Medium | T-1.03, T-5.07 | Ops defaults in docs | Documented |
| **T-11.07** ✅ Done | Backup/restore notes for Postgres volume + storage volume | Medium | T-3.02, T-0.03 | Runbook section | Runbook reviewed |
| **T-11.08** ✅ Done | Performance baseline notes (non-AI p95 target) | Low | T-2.02 | Measured baseline recorded | Doc updated |
| **T-11.09** ✅ Done | Data retention / erasure API design spike (P1) | Low | T-3.03, T-5.06 | Spec addendum only | Spike doc filed |

---

## Phase 12 — Deployment & Release

**Goal:** Staging-like Compose; migration discipline; release gate.  
**Phase exit:** PRD §20.3 release gate satisfied.

| ID | Task | Priority | Depends on | Deliverable | Exit criteria |
| --- | --- | --- | --- | --- | --- |
| **T-12.01** ✅ Done | Staging Compose overlay / env sample (no real secrets) | High | T-0.03, T-11.05 | Staging compose + `.env.staging.example` | Staging stack boots |
| **T-12.02** ✅ Done | Deployment runbook: migrate → api → worker → web order | High | T-0.06, T-4.02, T-12.01 | Runbook in docs/README | Operator dry-run OK |
| **T-12.03** ✅ Done | Release gate execution (PRD §20.3 eight checks) | High | T-9.04, T-9.05, T-10.06, T-11.02 | Signed gate record | All 8 checks pass |
| **T-12.04** ✅ Done | Tag v1.0.0 + changelog from phases | Medium | T-12.03 | Version tag notes | Tag published (when allowed) |
| **T-12.05** ✅ Done | Post-v1 backlog import (RAG, Ollama, S3, soft-tenant) | Low | T-12.03 | Backlog list linked to PRD §5.3 | Backlog visible |

---

## Phase 13 — Ollama Local LLM (v1.1)

**Goal:** Wire Ollama as a first-class `LlmProviderPort` (B-1.1-OLLAMA).  
**Phase exit:** `provider=ollama` works for chat/vision via factory + env; optional Compose profile.

| ID | Task | Priority | Depends on | Deliverable | Exit criteria |
| --- | --- | --- | --- | --- | --- |
| **T-13.01** ✅ Done | Implement `OllamaAdapter` (chat / vision / health) | High | T-5.10, T-5.04 | httpx → Ollama `/api/chat` | Unit tests pass with MockTransport |
| **T-13.02** ✅ Done | Alembic: add `ollama` to `ai_provider` enum | High | T-5.01 | Migration `0010_ai_provider_ollama` | Enum accepts ollama |
| **T-13.03** ✅ Done | Register ollama in `LlmFactory` + Settings + request DTOs | High | T-13.01 | `SUPPORTED_PROVIDERS` includes ollama | `AI_PRIMARY_PROVIDER=ollama` resolves |
| **T-13.04** ✅ Done | Compose optional `ollama` profile + env samples | Medium | T-13.03 | `docker compose --profile ollama` | Documented in usage.md |
| **T-13.05** ✅ Done | Docs: TASKS / usage / CHANGELOG / backlog status | Low | T-13.03 | Docs updated | Phase 13 marked Done |

---

## Phase 14 — S3-compatible Storage (v1.1)

**Goal:** Object storage behind the same `StoragePort` (B-P1-S3 / SDS ADR-014).  
**Phase exit:** `STORAGE_BACKEND=s3` works for documents/OCR/AI/pipelines; default remains local.

| ID | Task | Priority | Depends on | Deliverable | Exit criteria |
| --- | --- | --- | --- | --- | --- |
| **T-14.01** ✅ Done | Implement `S3StorageAdapter` (put/get/exists/delete + key layout) | High | T-3.02 | boto3 → S3/MinIO | Unit tests with mocked client |
| **T-14.02** ✅ Done | `get_storage()` factory + Settings (`STORAGE_BACKEND`, `S3_*`) | High | T-14.01 | `get_local_storage()` delegates to factory | `local` default; `s3` selectable |
| **T-14.03** ✅ Done | Compose optional `minio` profile + bucket init | Medium | T-14.02 | `docker compose --profile minio` | Documented in usage.md |
| **T-14.04** ✅ Done | Docs: TASKS / usage / CHANGELOG / backlog status | Low | T-14.02 | Docs updated | Phase 14 marked Done |

---

## Phase 15 — RAG minimal (v1.1)

**Goal:** Embeddings store + retrieval + citations behind ports (B-1.1-RAG / SDS ADR-016).  
**Phase exit:** Index OCR text → search top-k → chat with `document_ids` returns citations.

| ID | Task | Priority | Depends on | Deliverable | Exit criteria |
| --- | --- | --- | --- | --- | --- |
| **T-15.01** ✅ Done | `EmbeddingPort` + OpenAI / hash adapters | High | T-5.02 | `openai_embedding_adapter`, `hash_embedding_adapter` | Unit tests pass |
| **T-15.02** ✅ Done | `get_embedding()` factory + Settings | High | T-15.01 | `EMBEDDING_PROVIDER` | openai \| hash selectable |
| **T-15.03** ✅ Done | Chunking utility + cosine retrieve | High | T-15.01 | `rag_chunking.py` | Overlap chunks + ranking |
| **T-15.04** ✅ Done | `document_chunks` table + repository | High | T-3.01, T-4.01 | Alembic `0011_rag_chunks` | JSONB embeddings persist |
| **T-15.05** ✅ Done | `RagService` index + `/rag/index` `/rag/search` | High | T-15.04 | Router + service | Index from succeeded OCR |
| **T-15.06** ✅ Done | Chat RAG: `document_ids` + citations | High | T-15.05, T-5.06 | ChatRequest/Response extended | Citations in response |
| **T-15.07** ✅ Done | Docs: TASKS / usage / CHANGELOG / backlog | Low | T-15.06 | Docs updated | Phase 15 marked Done |

---

## Phase 16 — Soft multi-tenant (v1.2)

**Goal:** Additive `organizations` + `users.org_id` with org AI quota (B-1.2-TENANT / ADR-015).  
**Phase exit:** Default org backfill; `/orgs/me` + admin org CRUD; AI rate limit honors org override.

| ID | Task | Priority | Depends on | Deliverable | Exit criteria |
| --- | --- | --- | --- | --- | --- |
| **T-16.01** ✅ Done | `organizations` table + Alembic `0012` | High | T-1.01 | Model + migration | Enum + branding JSONB |
| **T-16.02** ✅ Done | `users.org_id` + default org backfill | High | T-16.01 | All users assigned | NOT NULL FK |
| **T-16.03** ✅ Done | `OrganizationRepository` + `OrganizationService` | High | T-16.02 | CRUD + effective quota | Unit tests pass |
| **T-16.04** ✅ Done | `/orgs/me` + `/admin/orgs` APIs | High | T-16.03 | Routers registered | Admin create/list/patch |
| **T-16.05** ✅ Done | Org-level AI Redis quota in `AiService` | High | T-16.03, T-5.07 | Dual user+org counters | 429 with scope=organization |
| **T-16.06** ✅ Done | `UserRead.org_id` + register/seed/admin patch | High | T-16.02 | Auth + admin wiring | New users join default org |
| **T-16.07** ✅ Done | Docs: TASKS / usage / CHANGELOG / backlog | Low | T-16.06 | Docs updated | Phase 16 marked Done |

---

## 3. Priority Index

### 3.1 High Priority (Critical Path / P0)

| ID | Title |
| --- | --- |
| T-0.01 | Repository layout |
| T-0.02 | Environment contract |
| T-0.03 | Compose Postgres + Redis |
| T-0.04 | Backend Docker + API shell |
| T-0.05 | Settings, logging, errors |
| T-0.06 | DB session + Alembic |
| T-0.07 | Redis + Health/Ready |
| T-1.01–T-1.06 | Auth core + tests |
| T-2.02, T-2.03, T-2.04, T-2.06 | Users, admin users, audit, tests |
| T-3.01–T-3.04 | Documents core + tests |
| T-4.01–T-4.05, T-4.08 | OCR async path + tests |
| T-5.01–T-5.06, T-5.11 | AI providers, prompts, chat/vision, tests |
| T-6.01, T-6.02, T-6.04 | Pipelines |
| T-7.01–T-7.03, T-7.06 | Statistics |
| T-8.01–T-8.04, T-8.06 | FE shell & auth |
| T-9.01–T-9.05 | FE feature consoles + user dashboard |
| T-10.01–T-10.04, T-10.06 | Admin APIs + core admin UI |
| T-11.01–T-11.05 | CI, smoke, OpenAPI, PR rules, security |
| T-12.01–T-12.03 | Staging, runbook, release gate |

### 3.2 Medium Priority

| ID | Title |
| --- | --- |
| T-0.08–T-0.10 | Entrypoint wait, FE docker, README |
| T-1.07 | Admin seed |
| T-2.01 | Permissions schema seed |
| T-3.05 | Idempotency-Key |
| T-4.06, T-4.07 | OCR retry, page limits |
| T-5.07–T-5.09 | AI quota, streaming, prompt seeds |
| T-6.03 | Partial stage failure UX/data |
| T-7.04 | Stats CSV export |
| T-8.05 | Shared UI primitives |
| T-9.06 | Personal charts |
| T-10.05, T-10.07, T-10.08 | Audit UI, prompt admin UI, QA checklist |
| T-11.06, T-11.07 | Rate-limit docs, backup notes |
| T-12.04 | Tag + changelog |

### 3.3 Low Priority

| ID | Title |
| --- | --- |
| T-0.11 | Script stubs beyond smoke |
| T-1.08 | Access jti denylist |
| T-2.05 | Permission helpers wiring |
| T-3.06 | Office/text ingest stubs |
| T-4.09 | Job reconciler |
| T-5.10 | Ollama stub |
| T-7.05 | Stats Redis cache |
| T-8.07 | FE lint polish |
| T-9.07, T-9.08 | Prompt browser, UX polish |
| T-11.08, T-11.09 | Perf baseline, erasure spike |
| T-12.05 | Post-v1 backlog import |

---

## 4. Suggested Sprint Slices (Optional Planning)

| Slice | Tasks | Outcome |
| --- | --- | --- |
| **Slice A — Platform** | T-0.01 … T-0.07 (+ T-0.08/0.10) | Compose green |
| **Slice B — Identity** | T-1.* + T-2.02 + T-8.01–T-8.04 | Login end-to-end |
| **Slice C — OCR Vertical** | T-3.* + T-4.* + T-9.01–T-9.02 | Upload→OCR in UI |
| **Slice D — AI Vertical** | T-5.* + T-9.03 | Chat/vision in UI |
| **Slice E — Pipeline + Stats** | T-6.* + T-7.* + T-9.04–T-9.05 | Full AI-first journey |
| **Slice F — Admin + Release** | T-10.* + T-11.* + T-12.* | Release gate |

---

## 5. Traceability

| Source | Mapping |
| --- | --- |
| PRD §19 phases | TASKS Phase 0–12 (expanded for FE/CI) |
| PRD P0/P1/P2 | High / Medium / Low |
| SDS ADR-001–032 | Constraints respected by task scopes |
| SDS §5 folders | T-0.01 |
| SDS §9 APIs | Phases 1–7, 10 API tasks |
| SDS §10 DB | Migration tasks `T-*.01` per domain |
| PRD §20.3 release gate | T-12.03 |

---

## 6. Rules for Adding/Changing Tasks

1. New work must reference PRD/SDS sections.  
2. Do not start a task until **Depends on** tasks are Done.  
3. Prefer splitting over merging if a task exceeds ~1–3 days.  
4. Priority changes require PRD priority alignment.  
5. **Do not** embed source code in this file; link PRs instead when implementing.

---

## 7. Document History

| Version | Date | Changes |
| --- | --- | --- |
| 1.0.0 | 2026-07-18 | Initial task breakdown from PRD + SDS |

---

## 8. Summary

`TASKS.md`는 인프라(Compose/DB/Redis)부터 인증·문서·OCR·AI·파이프라인·통계·프론트·관리자·CI·배포까지 **12 페이즈, 독립 구현 가능한 태스크**로 분해한다. 각 태스크는 **High/Medium/Low** 우선순위와 **Depends on** 관계를 가지며, 코드는 포함하지 않는다.
