# Software Design Specification (SDS)

| Field | Value |
| --- | --- |
| **Product Name** | AI SaaS Framework (AI Starter Framework) |
| **Document Type** | Software Design Specification |
| **Version** | 1.0.0 |
| **Status** | Approved for Implementation Planning |
| **Last Updated** | 2026-07-18 |
| **Parent Document** | [PRD.md](./PRD.md) v1.0.0 |
| **Audience** | Backend, Frontend, DevOps, QA, Security |
| **Code Generation** | This document does **not** include source code |

---

## 1. Purpose & Scope

본 SDS는 PRD v1.0.0을 엔지니어링 계약으로 구체화한다. 구현 시 본 문서의 **아키텍처 결정(ADR), 폴더, 계층, 의존성, 모듈, API, 데이터베이스**를 규범으로 따른다.

### 1.1 In Scope

- 시스템 컨텍스트·컨테이너·컴포넌트·계층 설계
- 전체 디렉터리 트리 및 폴더 책임
- 내부/외부 의존성 그래프
- 도메인 모듈 경계와 책임
- `/api/v1` 전 엔드포인트 계약
- PostgreSQL 물리 스키마 및 Redis 키 설계
- 배포·보안·오류·관측 설계

### 1.2 Out of Scope

- 소스 코드, 스니펫, PoC
- Kubernetes / MSA / Event Sourcing / CQRS
- RAG·Ollama 상세 설계 (v1.1)

---

## 2. System Context

### 2.1 Context Diagram (Logical)

```
┌──────────────┐     HTTPS/REST+JWT      ┌────────────────────┐
│  End User /  │ ◄─────────────────────► │  Next.js Web (web) │
│  Admin       │                         └─────────┬──────────┘
└──────────────┘                                   │ /api/v1
                                                   ▼
┌──────────────┐     HTTPS API Keys      ┌────────────────────┐
│ OpenAI API   │ ◄─────────────────────► │                    │
└──────────────┘                         │  FastAPI (api)     │
┌──────────────┐                         │  + Workers         │
│ Gemini API   │ ◄─────────────────────► │                    │
└──────────────┘                         └─────┬────────┬─────┘
                                               │        │
                                    ┌──────────▼──┐  ┌──▼─────────┐
                                    │ PostgreSQL  │  │   Redis    │
                                    │ (SoR)       │  │ (cache/q)  │
                                    └─────────────┘  └────────────┘
                                               │
                                    ┌──────────▼──────────────┐
                                    │ File Storage (local vol)│
                                    └─────────────────────────┘
```

### 2.2 Actors

| Actor | Interaction |
| --- | --- |
| End User | Web UI → API: upload, OCR, AI, personal stats |
| Admin | Web Admin → API: users, usage, OCR history, audit |
| Framework Developer | Docs + Compose + OpenAPI |
| External LLM Providers | Outbound HTTPS from api/worker |
| Ops | Docker Compose, env secrets, migrations |

---

## 3. Architecture Decision Records (ADR)

모든 결정은 **Accepted** 상태이며, 변경 시 새 ADR 버전과 PRD 정합이 필요하다.

### ADR-001 — Modular Monolith

| Field | Content |
| --- | --- |
| **Status** | Accepted |
| **Context** | MSA는 초기 복잡도·운영 비용이 과도함 (PRD Non-Goal) |
| **Decision** | 단일 배포 단위의 모듈형 모놀리스. 도메인은 패키지 경계로 분리 |
| **Consequences** | 단순 배포, 공유 DB 트랜잭션. 향후 서비스 분리는 모듈 경계 기준 |

### ADR-002 — API First Separation

| Field | Content |
| --- | --- |
| **Status** | Accepted |
| **Context** | FE/BE 병렬 개발, 클라이언트 교체 필요 |
| **Decision** | Next.js와 FastAPI를 프로세스·리포지토리 디렉터리로 완전 분리. 통신은 REST `/api/v1`만 |
| **Consequences** | Swagger로 BE 단독 검증. BFF는 v1에서 두지 않음 |

### ADR-003 — MVC + Service + Repository

| Field | Content |
| --- | --- |
| **Status** | Accepted |
| **Context** | Controller 비대화 방지, Laravel/Node 출신 온보딩 |
| **Decision** | Router(Controller) → Service → Repository → DB. Adapter는 Service만 호출 |
| **Consequences** | 테스트 용이. Controller→Repository 직접 호출 금지 (리뷰 게이트) |

### ADR-004 — FastAPI as Backend Framework

| Field | Content |
| --- | --- |
| **Status** | Accepted |
| **Decision** | FastAPI + Pydantic v2 스키마 + 의존성 주입 |
| **Consequences** | OpenAPI 자동 생성. async 엔드포인트 기본 |

### ADR-005 — Next.js App Router Frontend

| Field | Content |
| --- | --- |
| **Status** | Accepted |
| **Decision** | TypeScript + Next.js App Router. UI는 Presentation only |
| **Consequences** | `frontend/services`가 API 클라이언트 단일 진입점 |

### ADR-006 — PostgreSQL as System of Record

| Field | Content |
| --- | --- |
| **Status** | Accepted |
| **Decision** | 모든 비즈니스 영속 데이터는 PostgreSQL. SQLAlchemy 2.x + Alembic |
| **Consequences** | 단일 DB, soft multi-tenant는 v1 미도입 |

### ADR-007 — Redis for Ephemeral Coordination

| Field | Content |
| --- | --- |
| **Status** | Accepted |
| **Decision** | Redis는 SoR가 아님. Rate limit, refresh denylist, job queue, short cache만 |
| **Consequences** | Redis 유실 시 재로그인·재큐잉으로 복구 가능해야 함 |

### ADR-008 — JWT Access + Refresh Rotation

| Field | Content |
| --- | --- |
| **Status** | Accepted |
| **Decision** | Access: Bearer JWT (단기). Refresh: HttpOnly Secure Cookie + DB hash 저장 + Redis denylist. Refresh 회전(rotation) 필수 |
| **Rationale** | XSS에 강한 refresh, API 확장을 위한 Bearer access |
| **Consequences** | SameSite=Lax, CSRF 토큰(더블 서브밋) 적용 |

### ADR-009 — RBAC Roles (v1 Minimal) + Permissions (P1 Schema Ready)

| Field | Content |
| --- | --- |
| **Status** | Accepted |
| **Decision** | v1 런타임 인가: `admin` \| `user`. `permissions` / `role_permissions` 테이블은 스키마에 포함하고 API는 P1 |
| **Consequences** | 마이그레이션 한 번에 권한 확장 가능 |

### ADR-010 — Async Jobs via ARQ on Redis

| Field | Content |
| --- | --- |
| **Status** | Accepted |
| **Context** | OCR/긴 AI는 동기 HTTP에 부적합 |
| **Decision** | Worker 프레임워크는 **ARQ** (Async Redis Queue). API와 동일 이미지, 다른 커맨드 |
| **Consequences** | Celery 대비 의존성 단순. Redis Streams 직접 구현은 하지 않음 |

### ADR-011 — PaddleOCR + OpenCV Preprocess

| Field | Content |
| --- | --- |
| **Status** | Accepted |
| **Decision** | OCR 엔진 = PaddleOCR. 전처리 = OpenCV. 기본 언어: `korean+en`. CPU 기본 |
| **Consequences** | 이미지 크기·페이지 수 제한 필수. GPU는 환경 플래그 |

### ADR-012 — Dual LLM Providers with Adapter Port

| Field | Content |
| --- | --- |
| **Status** | Accepted |
| **Decision** | `LlmProviderPort` 구현체: OpenAIAdapter, GeminiAdapter. Primary 기본값 `openai`, Fallback `gemini` (P1 활성화 플래그) |
| **Consequences** | Service는 SDK를 import하지 않음. Adapter만 SDK 의존 |

### ADR-013 — Prompt Management as First-class Entity

| Field | Content |
| --- | --- |
| **Status** | Accepted |
| **Decision** | 프롬프트는 DB 버전 관리. 요청 시 name+version 또는 active 버전 resolve |
| **Consequences** | 코드 하드코딩 프롬프트 금지(시스템 부트스트랩 시드만 허용) |

### ADR-014 — Local Volume Storage with Port Abstraction

| Field | Content |
| --- | --- |
| **Status** | Accepted |
| **Decision** | v1 구현: 로컬/바인드 볼륨. `StoragePort` 인터페이스로 S3 호환 교체 예약. 실제 S3는 v1.1+ |
| **Consequences** | `documents.storage_key`는 provider-agnostic 경로 키 |

### ADR-015 — Soft Multi-Tenant (v1.2)

| Field | Content |
| --- | --- |
| **Status** | Superseded for v1.2+ (was: No Soft Multi-Tenant in v1) |
| **Decision** | v1: `org_id` 없음. **v1.2 (Phase 16):** additive `organizations` + `users.org_id`; 리소스 테이블은 간접 소속(user FK). Org AI quota + branding JSONB. |
| **Consequences** | 스키마/DB per-tenant 격리는 계속 Non-Goal. Org-scoped admin·리소스 `org_id` 컬럼은 후속. |

### ADR-016 — RAG Deferred to v1.1

| Field | Content |
| --- | --- |
| **Status** | Accepted |
| **Decision** | 벡터 DB·임베딩 테이블·검색 API는 v1에 포함하지 않음 |
| **Consequences** | Document/OCR 텍스트만 저장; 검색은 메타 필터 수준 |

### ADR-017 — Docker Compose First Runtime

| Field | Content |
| --- | --- |
| **Status** | Accepted |
| **Decision** | 로컬·스테이징·소규모 운영의 기준 런타임은 Compose. 서비스: `api`, `worker`, `web`, `postgres`, `redis` |
| **Consequences** | K8s는 Non-Goal |

### ADR-018 — Alembic Exclusive Schema Evolution

| Field | Content |
| --- | --- |
| **Status** | Accepted |
| **Decision** | 스키마 변경은 Alembic만. 런타임 `create_all` 금지(테스트 제외) |
| **Consequences** | 배포 파이프라인에 `alembic upgrade head` |

### ADR-019 — Error Envelope & Request ID

| Field | Content |
| --- | --- |
| **Status** | Accepted |
| **Decision** | 모든 에러 응답: `{ code, message, details, request_id }`. `X-Request-ID` 미들웨어 전파 |
| **Consequences** | FE/로그 상관관계 통일 |

### ADR-020 — Pagination Standard

| Field | Content |
| --- | --- |
| **Status** | Accepted |
| **Decision** | Offset 페이지네이션: `page` (1-based), `page_size` (default 20, max 100). 응답: `{ items, page, page_size, total }` |
| **Consequences** | Audit/Usage 대용량은 추후 cursor 옵션(ADR 개정) |

### ADR-021 — Idempotency for Uploads (P1 Ready)

| Field | Content |
| --- | --- |
| **Status** | Accepted (schema/header reserved) |
| **Decision** | `Idempotency-Key` 헤더 지원을 Document/Pipeline POST에 P1로 구현. 키는 Redis TTL 24h |
| **Consequences** | v1 P0는 없어도 동작; 헤더 무시하지 말고 문서화 |

### ADR-022 — Statistics Materialization

| Field | Content |
| --- | --- |
| **Status** | Accepted |
| **Decision** | `stat_daily` 테이블에 일 배치/증분 upsert. 월간은 daily rollup 쿼리 |
| **Consequences** | 실시간 exact count는 admin 한정 raw query 허용 |

### ADR-023 — Password Hashing

| Field | Content |
| --- | --- |
| **Status** | Accepted |
| **Decision** | Argon2id (우선) 또는 bcrypt. 평문·가역 암호화 금지 |
| **Consequences** | 검증 시간으로 timing 방어는 라이브러리 기본 사용 |

### ADR-024 — Sync vs Async OCR Boundary

| Field | Content |
| --- | --- |
| **Status** | Accepted |
| **Decision** | 모든 OCR Job은 비동기. 동기 OCR API 없음 |
| **Consequences** | 클라이언트는 폴링 `GET /ocr/jobs/{id}` |

### ADR-025 — Defense in Depth Authorization

| Field | Content |
| --- | --- |
| **Status** | Accepted |
| **Decision** | Router dependency에서 인증·역할 검사 + Service에서 소유권/민감 연산 재검증 |
| **Consequences** | 실수로 공개된 라우터도 Service에서 차단 가능해야 함 |

### ADR-026 — Logging Privacy

| Field | Content |
| --- | --- |
| **Status** | Accepted |
| **Decision** | 구조화 JSON 로그. password, token, API key, Authorization 헤더 금지. 문서 본문은 debug에서만 샘플 길이 제한 |
| **Consequences** | 감사는 `audit_logs` 테이블 사용 |

### ADR-027 — API Versioning

| Field | Content |
| --- | --- |
| **Status** | Accepted |
| **Decision** | Prefix `/api/v1`. Breaking change는 `/api/v2`. 하위호환 필드 추가는 v1에 additive |
| **Consequences** | 구버전 폐기는 별도 공지 정책 |

### ADR-028 — Health vs Readiness

| Field | Content |
| --- | --- |
| **Status** | Accepted |
| **Decision** | `GET /health` = 프로세스 liveness. `GET /ready` = PostgreSQL + Redis ping |
| **Consequences** | 오케스트레이터/로드밸런서 분리 프로브 |

### ADR-029 — Frontend Token Handling

| Field | Content |
| --- | --- |
| **Status** | Accepted |
| **Decision** | Access token: 메모리(또는 짧은 session). Refresh: HttpOnly cookie 자동. FE는 raw fetch 남용 금지, `frontend/services` 경유 |
| **Consequences** | SSR에서 쿠키 전달 시 서버 라우트 핸들러로 프록시하지 않음(v1); 브라우저는 직접 API origin 호출 (CORS) |

### ADR-030 — CORS Allowlist

| Field | Content |
| --- | --- |
| **Status** | Accepted |
| **Decision** | `CORS_ORIGINS` 환경변수 콤마 목록만 허용. credentials=true (refresh cookie) |
| **Consequences** | `*` 금지 (credentials 모드) |

### ADR-031 — Testing Strategy Alignment

| Field | Content |
| --- | --- |
| **Status** | Accepted |
| **Decision** | Unit(service/adapter mock) + Integration(Postgres/Redis testcontainers 또는 compose profile) + API tests + Compose smoke |
| **Consequences** | Provider 실호출은 CI optional/manual |

### ADR-032 — Documentation-Before-Code Policy

| Field | Content |
| --- | --- |
| **Status** | Accepted |
| **Decision** | Spec → Implementation → Test → Docs. SDS/PRD 미반영 기능 금지 |
| **Consequences** | PR 템플릿에 Spec 링크 필수 |

---

## 4. Logical Layers

### 4.1 Layer Stack

```
[ Presentation ]
   Next.js pages/components/hooks
           │ HTTPS REST
[ Transport / Controller ]
   FastAPI routers + middleware + schemas (DTO)
           │
[ Application / Service ]
   use-case orchestration, policies, transactions
           │                    │
[ Repository ]           [ Adapters / Ports ]
   SQLAlchemy DAO         OpenAI, Gemini, PaddleOCR,
           │               OpenCV, Storage, ARQ enqueue
[ Infrastructure ]
   PostgreSQL · Redis · Filesystem · Docker network
```

### 4.2 Layer Catalog

| Layer | Location | Responsibility | Allowed Dependencies | Forbidden |
| --- | --- | --- | --- | --- |
| **Presentation** | `frontend/**` | UX, form state, polling, charts | `frontend/services`, types | Direct SQL, provider SDK |
| **Controller** | `backend/app/routers` | HTTP mapping, status codes, Depends | services, schemas, core.deps | repositories, models session SQL, adapters |
| **Schema (DTO)** | `backend/app/schemas` | Request/Response validation | pydantic, enums | DB session, services |
| **Middleware** | `backend/app/middleware` | request_id, logging, CORS hooks | core | business services (thin only) |
| **Service** | `backend/app/services` | Business rules, orchestration | repositories, adapters(ports), core | FastAPI Request (prefer), raw SQL |
| **Repository** | `backend/app/repositories` | CRUD/query | models, SQLAlchemy session | HTTP, OCR/LLM SDK |
| **Model** | `backend/app/models` | ORM entities / table mapping | SQLAlchemy | Pydantic API schemas mix-in |
| **Adapter** | `backend/app/adapters` (or `utils/providers`) | External I/O | vendor SDK, core.settings | repositories (prefer return DTO to service) |
| **Worker** | `backend/app/workers` | Async job handlers | services or domain job services, adapters | routers, Next.js |
| **Core** | `backend/app/core` | settings, security, db, redis, di | stdlib, libs | domain business rules |
| **Exceptions** | `backend/app/exceptions` | domain/app errors | — | framework leak preferably mapped in handler |
| **Tests** | `backend/app/tests` | verification | all (test doubles) | production secrets |

### 4.3 Dependency Direction Rules

1. **단방향:** Controller → Service → Repository → Model/DB  
2. Service → Adapter(Port) 허용  
3. Repository → Service **금지**  
4. Adapter → Service **금지** (콜백 필요 시 이벤트/큐로만)  
5. Frontend → Backend: HTTP만  
6. Worker는 Service를 호출할 수 있으나 Router를 import **금지**

### 4.4 MVC Mapping

| MVC | SDS Mapping |
| --- | --- |
| Model | `models` + persistence via `repositories` |
| View | Next.js UI; API JSON은 machine-readable view |
| Controller | FastAPI `routers` |

---

## 5. Folder Structure — Complete Description

### 5.1 Repository Root

| Path | Purpose |
| --- | --- |
| `README.md` | 제품 소개, 기동, 아키텍처 요약, 기여 가이드 |
| `.env.example` | 모든 환경변수 키·설명·샘플(비밀값 없음) |
| `docker-compose.yml` | api, worker, web, postgres, redis 오케스트레이션 |
| `docs/` | PRD, SDS, 후속 스펙 |
| `docker/` | Dockerfile 및 컨테이너 보조 설정 |
| `scripts/` | 개발·배포 헬퍼(마이그레이션 래퍼, 시드, smoke) |
| `.github/` | CI workflows, PR 템플릿 |
| `backend/` | FastAPI 애플리케이션 |
| `frontend/` | Next.js 애플리케이션 |

### 5.2 `docs/`

| Path | Purpose |
| --- | --- |
| `docs/PRD.md` | 제품 요구사항 |
| `docs/SDS.md` | 본 설계 명세 |
| `docs/` (future) | API 변경 노트, 보안 점검 체크리스트 등 |

### 5.3 `docker/`

| Path | Purpose |
| --- | --- |
| `docker/backend.Dockerfile` | API/Worker 공용 이미지 빌드 정의 |
| `docker/frontend.Dockerfile` | Next.js 빌드·런 이미지 |
| `docker/backend.entrypoint.sh` | 대기(wait-for db/redis), 선택적 migrate, 프로세스 기동 |
| `docker/frontend.entrypoint.sh` | FE 기동 엔트리 |
| `docker/nginx/` (optional) | 향후 TLS 종료용 — v1 optional, Compose에 기본 미포함 가능 |

### 5.4 `scripts/`

| Path | Purpose |
| --- | --- |
| `scripts/dev-up` | Compose 기동 래퍼 설명/스크립트 |
| `scripts/migrate` | Alembic upgrade 래퍼 |
| `scripts/seed` | 관리자·프롬프트 시드 |
| `scripts/smoke` | health + login smoke |

### 5.5 `.github/`

| Path | Purpose |
| --- | --- |
| `.github/workflows/ci.yml` | lint, test, build images |
| `.github/PULL_REQUEST_TEMPLATE.md` | Spec 링크·레이어 체크리스트 |

### 5.6 `backend/`

| Path | Purpose |
| --- | --- |
| `backend/pyproject.toml` 또는 `requirements.txt` | Python 의존성 선언 |
| `backend/alembic.ini` | Alembic 설정 |
| `backend/alembic/` | 마이그레이션 환경 |
| `backend/alembic/env.py` | 메타데이터·연결 훅 |
| `backend/alembic/versions/` | 리비전 스크립트 |
| `backend/app/` | 애플리케이션 패키지 루트 |
| `backend/app/main.py` | FastAPI app factory, router include |
| `backend/app/core/` | 설정·보안·DB·Redis·DI |
| `backend/app/routers/` | Controllers |
| `backend/app/services/` | Business services |
| `backend/app/repositories/` | Data access |
| `backend/app/models/` | SQLAlchemy models |
| `backend/app/schemas/` | Pydantic DTO |
| `backend/app/middleware/` | HTTP middleware |
| `backend/app/exceptions/` | 예외 타입·핸들러 등록 대상 |
| `backend/app/adapters/` | 외부 시스템 어댑터 |
| `backend/app/utils/` | 순수 헬퍼(해시, 시간, 파일 MIME) |
| `backend/app/workers/` | ARQ worker settings & jobs |
| `backend/app/tests/` | 테스트 |

### 5.7 `backend/app/core/` (파일 단위 책임)

| Path | Purpose |
| --- | --- |
| `core/config.py` | Settings (env) |
| `core/security.py` | JWT issue/verify, password hash |
| `core/database.py` | Engine, Session factory |
| `core/redis.py` | Redis client factory |
| `core/deps.py` | FastAPI Depends: db, current_user, roles |
| `core/logging.py` | Structured logging setup |
| `core/constants.py` | Enums, limits (no magic) |

### 5.8 `backend/app/routers/`

| Path | Purpose |
| --- | --- |
| `routers/health.py` | `/health`, `/ready` |
| `routers/auth.py` | login/refresh/logout/register |
| `routers/users.py` | `/users/me` |
| `routers/documents.py` | document upload/list/get/delete |
| `routers/ocr.py` | OCR jobs |
| `routers/ai.py` | chat, vision, prompts |
| `routers/pipelines.py` | pipeline runs |
| `routers/stats.py` | daily/monthly stats |
| `routers/admin/users.py` | admin user management |
| `routers/admin/usage.py` | AI usage |
| `routers/admin/ocr_history.py` | OCR history |
| `routers/admin/audit.py` | audit logs |

### 5.9 `backend/app/services/`

| Path | Purpose |
| --- | --- |
| `services/auth_service.py` | 인증·토큰·로그아웃·rate limit 조율 |
| `services/user_service.py` | 사용자 프로필·상태 |
| `services/document_service.py` | 업로드 검증·저장·메타 |
| `services/ocr_service.py` | Job 생성·상태·결과 조회 |
| `services/ai_service.py` | chat/vision orchestration, usage |
| `services/prompt_service.py` | 프롬프트 CRUD·resolve |
| `services/pipeline_service.py` | OCR→AI 파이프라인 오케스트레이션 |
| `services/stats_service.py` | 집계 조회·materialize 트리거 |
| `services/admin_service.py` | 관리자 유스케이스 facade |
| `services/audit_service.py` | 감사 기록 |

### 5.10 `backend/app/repositories/`

| Path | Purpose |
| --- | --- |
| `repositories/user_repository.py` | users |
| `repositories/refresh_token_repository.py` | refresh tokens |
| `repositories/permission_repository.py` | permissions (P1) |
| `repositories/document_repository.py` | documents |
| `repositories/ocr_job_repository.py` | ocr_jobs |
| `repositories/ocr_result_repository.py` | ocr_results |
| `repositories/ai_prompt_repository.py` | ai_prompts |
| `repositories/ai_request_repository.py` | ai_requests |
| `repositories/ai_usage_repository.py` | ai_usages |
| `repositories/pipeline_run_repository.py` | pipeline_runs |
| `repositories/audit_log_repository.py` | audit_logs |
| `repositories/stat_daily_repository.py` | stat_daily |

### 5.11 `backend/app/models/`

| Path | Purpose |
| --- | --- |
| `models/base.py` | Declarative base, mixins (id, timestamps) |
| `models/user.py` | User |
| `models/permission.py` | Permission, RolePermission |
| `models/refresh_token.py` | RefreshToken |
| `models/document.py` | Document |
| `models/ocr.py` | OcrJob, OcrResult |
| `models/ai.py` | AiPrompt, AiRequest, AiUsage |
| `models/pipeline.py` | PipelineRun |
| `models/audit.py` | AuditLog |
| `models/stats.py` | StatDaily |

### 5.12 `backend/app/schemas/`

| Path | Purpose |
| --- | --- |
| `schemas/common.py` | Page, ErrorEnvelope, IDs |
| `schemas/auth.py` | Login, Token pair responses |
| `schemas/user.py` | User read/update |
| `schemas/document.py` | Document DTOs |
| `schemas/ocr.py` | Job create/status/result |
| `schemas/ai.py` | Chat, Vision, Prompt DTOs |
| `schemas/pipeline.py` | Pipeline DTOs |
| `schemas/stats.py` | Series points |
| `schemas/admin.py` | Admin list filters |

### 5.13 `backend/app/adapters/`

| Path | Purpose |
| --- | --- |
| `adapters/ports.py` | Protocol/ABC: LlmProviderPort, OcrEnginePort, StoragePort, ImagePreprocessPort |
| `adapters/openai_adapter.py` | OpenAI 구현 |
| `adapters/gemini_adapter.py` | Gemini 구현 |
| `adapters/paddle_ocr_adapter.py` | PaddleOCR 구현 |
| `adapters/opencv_preprocess_adapter.py` | OpenCV 전처리 |
| `adapters/local_storage_adapter.py` | 로컬 파일 저장 |
| `adapters/llm_factory.py` | provider 선택·fallback |
| `adapters/queue_publisher.py` | ARQ enqueue 래퍼 |

### 5.14 `backend/app/middleware/`

| Path | Purpose |
| --- | --- |
| `middleware/request_id.py` | X-Request-ID |
| `middleware/access_log.py` | access structured log |

### 5.15 `backend/app/exceptions/`

| Path | Purpose |
| --- | --- |
| `exceptions/base.py` | AppError hierarchy |
| `exceptions/auth.py` | Unauthorized, Forbidden, Token errors |
| `exceptions/domain.py` | NotFound, Conflict, Validation |
| `exceptions/providers.py` | ProviderTimeout, RateLimited, ProviderAuth |

### 5.16 `backend/app/utils/`

| Path | Purpose |
| --- | --- |
| `utils/files.py` | MIME sniff, checksum, size |
| `utils/time.py` | UTC helpers |
| `utils/pagination.py` | page math |

### 5.17 `backend/app/workers/`

| Path | Purpose |
| --- | --- |
| `workers/settings.py` | ARQ Redis settings |
| `workers/ocr_jobs.py` | OCR job function |
| `workers/pipeline_jobs.py` | pipeline job function |
| `workers/stats_jobs.py` | daily materialize job |

### 5.18 `backend/app/tests/`

| Path | Purpose |
| --- | --- |
| `tests/unit/` | service/adapter unit |
| `tests/integration/` | repository/db/redis |
| `tests/api/` | router contract tests |

### 5.19 `frontend/`

| Path | Purpose |
| --- | --- |
| `frontend/package.json` | Node 의존성 |
| `frontend/next.config.*` | Next 설정 |
| `frontend/tsconfig.json` | TS 설정 |
| `frontend/public/` | 정적 자산 |
| `frontend/app/` | App Router routes |
| `frontend/components/` | UI 컴포넌트 |
| `frontend/hooks/` | React hooks |
| `frontend/lib/` | 순수 유틸, auth token helpers |
| `frontend/services/` | Backend API clients |
| `frontend/types/` | 공유 TS 타입 |

### 5.20 `frontend/app/` routes

| Path | Purpose |
| --- | --- |
| `app/(auth)/login/page` | 로그인 |
| `app/(auth)/register/page` | 회원가입 |
| `app/(app)/dashboard/page` | 사용자 대시보드 |
| `app/(app)/documents/page` | 문서·업로드 |
| `app/(app)/ocr/page` | OCR 콘솔 |
| `app/(app)/ai/page` | AI chat/vision |
| `app/(app)/pipelines/page` | 파이프라인 |
| `app/(admin)/admin/page` | 관리자 홈 |
| `app/(admin)/admin/users/page` | 사용자 관리 |
| `app/(admin)/admin/usage/page` | AI 사용량 |
| `app/(admin)/admin/ocr/page` | OCR 이력 |
| `app/(admin)/admin/audit/page` | 감사 로그 |
| `app/layout.tsx` | 루트 레이아웃 |
| `app/page.tsx` | 랜딩/리다이렉트 |

### 5.21 `frontend/components/`

| Path | Purpose |
| --- | --- |
| `components/ui/` | 버튼, 입력, 테이블, 모달 등 원자 |
| `components/auth/` | 로그인 폼 |
| `components/documents/` | 업로더 |
| `components/ocr/` | job status |
| `components/ai/` | chat panel |
| `components/stats/` | charts |
| `components/admin/` | admin tables |
| `components/layout/` | shell, nav, guard |

### 5.22 `frontend/services/`

| Path | Purpose |
| --- | --- |
| `services/http.ts` | base client, auth header, refresh intercept |
| `services/auth.ts` | auth API |
| `services/users.ts` | users API |
| `services/documents.ts` | documents API |
| `services/ocr.ts` | ocr API |
| `services/ai.ts` | ai API |
| `services/pipelines.ts` | pipelines API |
| `services/stats.ts` | stats API |
| `services/admin.ts` | admin API |

---

## 6. Dependency Catalog

### 6.1 Runtime Process Dependencies

| Consumer | Depends On | Protocol | Required |
| --- | --- | --- | --- |
| `web` | `api` | HTTPS REST | Yes |
| `api` | `postgres` | SQL | Yes |
| `api` | `redis` | Redis protocol | Yes |
| `api` | File volume | FS | Yes |
| `api` | OpenAI | HTTPS | Config-dependent |
| `api` | Gemini | HTTPS | Config-dependent |
| `worker` | `postgres` | SQL | Yes |
| `worker` | `redis` | Redis | Yes |
| `worker` | File volume | FS | Yes |
| `worker` | OpenAI/Gemini | HTTPS | Pipeline/AI jobs |
| `worker` | PaddleOCR/OpenCV | In-process | OCR jobs |

### 6.2 Internal Module Dependency Graph

```
routers/*          → services/*, schemas/*, core.deps, exceptions
services/*         → repositories/*, adapters (ports), core, exceptions
repositories/*     → models/*, core.database
adapters/*         → vendor SDKs, core.config, ports
workers/*          → services/* (job entry), adapters, core
middleware/*       → core.logging
main               → routers, middleware, exceptions handlers, core
frontend pages     → frontend/services, hooks, components
frontend/services  → backend /api/v1 only
```

### 6.3 Backend External Libraries (Normative Intent)

| Dependency | Used By | Purpose |
| --- | --- | --- |
| fastapi | api | HTTP framework |
| uvicorn | api | ASGI server |
| pydantic / pydantic-settings | core, schemas | validation, settings |
| sqlalchemy | models, repositories | ORM |
| alembic | migrations | schema versioning |
| asyncpg 또는 psycopg | database driver | PostgreSQL |
| redis | core, workers | cache/queue/rate limit |
| arq | workers, queue publisher | job queue |
| python-jose 또는 PyJWT | security | JWT |
| passlib[argon2] 또는 argon2-cffi | security | password hashing |
| httpx | adapters | outbound HTTP |
| openai (official SDK) | openai_adapter | LLM |
| google-genai 또는 generativeai | gemini_adapter | LLM |
| paddleocr | paddle_ocr_adapter | OCR |
| opencv-python-headless | opencv adapter | preprocess |
| python-multipart | routers | file upload |
| orjson (optional) | api | JSON performance |

> 정확한 버전 핀은 구현 착수 시 lockfile에서 고정한다. SDS는 **역할**을 규범화한다.

### 6.4 Frontend External Libraries (Normative Intent)

| Dependency | Purpose |
| --- | --- |
| next | App framework |
| react / react-dom | UI |
| typescript | typing |
| 차트 라이브러리 (선택: recharts 등) | dashboard charts |
| 폼/검증 (선택) | login/upload forms |

FE는 Backend SDK를 직접 생성하지 않고 `frontend/services` 수동 typed client를 v1 표준으로 한다.

### 6.5 Infrastructure Dependencies

| Component | Image/Tech | Persists |
| --- | --- | --- |
| PostgreSQL 16+ | official image | Yes (volume) |
| Redis 7+ | official image | Optional AOF; v1 tolerate loss for denylist |
| Docker Engine + Compose | host | — |

### 6.6 Environment Variable Dependencies

| Variable | Consumed By | Purpose |
| --- | --- | --- |
| `APP_ENV` | api, worker, web | local/staging/production |
| `DATABASE_URL` | api, worker | PostgreSQL DSN |
| `REDIS_URL` | api, worker | Redis DSN |
| `JWT_SECRET` | api | signing key |
| `JWT_ALGORITHM` | api | e.g. HS256 |
| `ACCESS_TOKEN_TTL_MINUTES` | api | access lifetime |
| `REFRESH_TOKEN_TTL_DAYS` | api | refresh lifetime |
| `CORS_ORIGINS` | api | allowlist |
| `OPENAI_API_KEY` | api, worker | OpenAI |
| `GEMINI_API_KEY` | api, worker | Gemini |
| `AI_PRIMARY_PROVIDER` | api, worker | `openai` \| `gemini` |
| `AI_FALLBACK_PROVIDER` | api, worker | optional |
| `AI_FALLBACK_ENABLED` | api, worker | bool |
| `STORAGE_PATH` | api, worker | local root |
| `OCR_LANG` | worker | default `korean+en` |
| `OCR_MAX_PAGES` | api, worker | limit |
| `UPLOAD_MAX_BYTES` | api | size limit |
| `NEXT_PUBLIC_API_BASE_URL` | web | API origin |

---

## 7. Module Design

각 모듈은 **경계, 책임, 소유 테이블, 공개 API, 의존 모듈**을 가진다.

### 7.1 Module: Health

| Item | Description |
| --- | --- |
| **Responsibility** | Liveness/readiness |
| **Tables** | none |
| **APIs** | `GET /health`, `GET /ready` |
| **Depends** | database ping, redis ping |

### 7.2 Module: Auth

| Item | Description |
| --- | --- |
| **Responsibility** | Register, login, refresh rotation, logout, password verify, auth rate limit |
| **Tables** | `users`, `refresh_tokens` (+ Redis denylist/rate keys) |
| **Services** | AuthService |
| **Repos** | UserRepository, RefreshTokenRepository |
| **Adapters** | Redis |
| **APIs** | `/api/v1/auth/*` |

### 7.3 Module: Users

| Item | Description |
| --- | --- |
| **Responsibility** | Profile read/update; status checks |
| **Tables** | `users` |
| **APIs** | `/api/v1/users/me` |
| **Depends** | Auth (current user) |

### 7.4 Module: Admin Users

| Item | Description |
| --- | --- |
| **Responsibility** | List/search users, activate/deactivate, role change |
| **Tables** | `users`, `audit_logs` |
| **APIs** | `/api/v1/admin/users*` |
| **Authz** | role=`admin` |

### 7.5 Module: Documents

| Item | Description |
| --- | --- |
| **Responsibility** | Multipart upload, MIME/size validation, checksum, metadata lifecycle |
| **Tables** | `documents` |
| **Adapters** | StoragePort |
| **APIs** | `/api/v1/documents*` |

### 7.6 Module: OCR

| Item | Description |
| --- | --- |
| **Responsibility** | Create async OCR jobs, preprocess options, persist results, history |
| **Tables** | `ocr_jobs`, `ocr_results` |
| **Adapters** | ImagePreprocessPort, OcrEnginePort, Queue |
| **APIs** | `/api/v1/ocr/*` |
| **Worker** | `ocr_jobs.run_ocr_job` |

### 7.7 Module: AI

| Item | Description |
| --- | --- |
| **Responsibility** | Chat, vision, provider selection, usage metering |
| **Tables** | `ai_requests`, `ai_usages` |
| **Adapters** | LlmProviderPort / factory |
| **APIs** | `/api/v1/ai/chat`, `/api/v1/ai/vision` |

### 7.8 Module: Prompts

| Item | Description |
| --- | --- |
| **Responsibility** | Versioned prompt templates |
| **Tables** | `ai_prompts` |
| **APIs** | `/api/v1/ai/prompts*` |
| **Authz** | write: admin (v1); read: authenticated |

### 7.9 Module: Pipelines

| Item | Description |
| --- | --- |
| **Responsibility** | Orchestrate Document → Preprocess → OCR → AI → Persist stages |
| **Tables** | `pipeline_runs` (+ references documents/ocr/ai) |
| **APIs** | `/api/v1/pipelines/*` |
| **Worker** | `pipeline_jobs.run_pipeline` |

### 7.10 Module: Statistics

| Item | Description |
| --- | --- |
| **Responsibility** | Daily/monthly metrics for dashboards |
| **Tables** | `stat_daily` |
| **APIs** | `/api/v1/stats/*` |
| **Worker** | periodic materialize |

### 7.11 Module: Admin Usage & OCR History & Audit

| Item | Description |
| --- | --- |
| **Responsibility** | Cross-user operational visibility |
| **Tables** | `ai_usages`, `ocr_jobs`, `ocr_results`, `audit_logs` |
| **APIs** | `/api/v1/admin/usage`, `/admin/ocr-history`, `/admin/audit-logs` |

### 7.12 Module: Frontend Shell

| Item | Description |
| --- | --- |
| **Responsibility** | Auth guards, navigation, role-based route groups |
| **Depends** | all FE services |

### 7.13 Cross-Cutting: Security Core

| Item | Description |
| --- | --- |
| **Responsibility** | JWT, password hashing, deps for roles |
| **Used by** | all protected modules |

### 7.14 Cross-Cutting: Observability

| Item | Description |
| --- | --- |
| **Responsibility** | request_id, structured logs, audit writes on admin mutations |

---

## 8. Sequence Designs (Key Flows)

### 8.1 Login

1. Client `POST /auth/login` with email/password  
2. AuthService rate-limit check (Redis)  
3. UserRepository load by email  
4. Verify password hash  
5. Issue access JWT; create refresh (hash to DB, set HttpOnly cookie)  
6. Audit optional: login success/fail  
7. Return access token + user summary  

### 8.2 Refresh

1. Browser sends refresh cookie to `POST /auth/refresh` (+ CSRF header)  
2. Validate cookie token, lookup hash, ensure not revoked/denylisted  
3. Rotate: revoke old, issue new refresh + new access  
4. Reuse detection → revoke all user refresh tokens  

### 8.3 OCR Job

1. User uploads document (or references `document_id`)  
2. `POST /ocr/jobs` → OcrService creates `queued` row, enqueues ARQ  
3. Worker loads file via StoragePort → OpenCV → PaddleOCR  
4. Writes `ocr_results`, sets job `succeeded`/`failed`  
5. Stats counters updated (inline or deferred job)  
6. Client polls `GET /ocr/jobs/{id}`  

### 8.4 AI Chat

1. `POST /ai/chat` with messages and optional `prompt_name`  
2. PromptService resolve template  
3. LlmFactory → primary adapter  
4. On failure + fallback enabled → secondary  
5. Persist AiRequest + AiUsage  
6. Return content + usage summary  

### 8.5 Pipeline

1. `POST /pipelines/runs` with document_id + options  
2. Create PipelineRun `queued`, enqueue  
3. Worker stages: preprocess → ocr → ai_analyze → persist stage JSON  
4. Client polls run status  

---

## 9. API Specification (Complete v1 Catalogue)

**Base URL:** `/api/v1`  
**Auth header:** `Authorization: Bearer <access_token>` (unless noted)  
**Refresh cookie name:** `refresh_token` (HttpOnly; Secure in non-local)  
**CSRF header (refresh/logout cookie ops):** `X-CSRF-Token`  
**Error body:** `{ "code": string, "message": string, "details": object|null, "request_id": string }`  
**Pagination query:** `page`, `page_size`  
**Pagination body:** `{ "items": [], "page": n, "page_size": n, "total": n }`

### 9.1 Health

| Method | Path | Auth | Description | Request | Response |
| --- | --- | --- | --- | --- | --- |
| GET | `/health` | Public | Liveness | — | `{ "status": "ok" }` |
| GET | `/ready` | Public | Readiness | — | `{ "status": "ok", "postgres": true, "redis": true }` or 503 |

> Health routes may be mounted at root `/health`, `/ready` **and/or** under `/api/v1` equivalently; **normative public probes:** `/health`, `/ready` (no version prefix) for orchestrators. Versioned duplicates optional.

### 9.2 Auth — `/api/v1/auth`

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| POST | `/api/v1/auth/register` | Public | 회원가입 |
| POST | `/api/v1/auth/login` | Public | 로그인, access 반환, refresh cookie set |
| POST | `/api/v1/auth/refresh` | Refresh cookie + CSRF | access 재발급, refresh 회전 |
| POST | `/api/v1/auth/logout` | Access or Refresh+CSRF | refresh revoke + cookie clear |
| GET | `/api/v1/auth/csrf` | Public/Session | CSRF 토큰 발급(쿠키 병행) |

#### POST `/api/v1/auth/register`

- **Body:** `{ "email": string, "password": string, "name": string }`
- **Responses:** `201` `{ user }`; `409` email exists; `422` validation
- **Side effects:** user role=`user`, status=`active`

#### POST `/api/v1/auth/login`

- **Body:** `{ "email": string, "password": string }`
- **Responses:** `200` `{ "access_token": string, "token_type": "bearer", "expires_in": number, "user": UserRead }`
- **Set-Cookie:** `refresh_token=...; HttpOnly; Secure; SameSite=Lax; Path=/api/v1/auth`
- **Errors:** `401` invalid; `429` rate limited; `403` inactive user

#### POST `/api/v1/auth/refresh`

- **Body:** empty or `{}`
- **Headers:** `X-CSRF-Token`
- **Responses:** `200` same shape as login (without full user optional; normative: include `user`)
- **Errors:** `401` invalid/reused; `403` CSRF

#### POST `/api/v1/auth/logout`

- **Responses:** `204`
- **Side effects:** revoke refresh, clear cookie, optional access jti denylist (P1)

#### GET `/api/v1/auth/csrf`

- **Responses:** `200` `{ "csrf_token": string }` + CSRF cookie if double-submit

### 9.3 Users — `/api/v1/users`

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/api/v1/users/me` | User | 내 프로필 |
| PATCH | `/api/v1/users/me` | User | 이름 등 수정 (email 변경 v1 비허용 또는 admin-only) |

#### GET `/api/v1/users/me`

- **Response `200`:** `{ "id", "email", "name", "role", "status", "created_at", "updated_at" }`

#### PATCH `/api/v1/users/me`

- **Body:** `{ "name"?: string }`
- **Response `200`:** UserRead

### 9.4 Documents — `/api/v1/documents`

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| POST | `/api/v1/documents` | User | 파일 업로드 |
| GET | `/api/v1/documents` | User | 내 문서 목록 |
| GET | `/api/v1/documents/{document_id}` | User | 문서 메타 |
| DELETE | `/api/v1/documents/{document_id}` | User | 소프트/하드 삭제(v1: soft status=`deleted`) |

#### POST `/api/v1/documents`

- **Content-Type:** `multipart/form-data`
- **Fields:** `file` (required)
- **Headers (P1):** `Idempotency-Key`
- **Constraints:** MIME ∈ {image/jpeg, image/png, image/webp, application/pdf}; size ≤ `UPLOAD_MAX_BYTES`
- **Response `201`:** DocumentRead `{ id, filename, mime_type, size_bytes, checksum_sha256, status, created_at }`
- **Errors:** `413` too large; `415` unsupported; `422`

#### GET `/api/v1/documents`

- **Query:** pagination + optional `status`
- **Response `200`:** Page[DocumentRead]

#### GET `/api/v1/documents/{document_id}`

- **Authz:** owner or admin
- **Response `200`:** DocumentRead; `404`

#### DELETE `/api/v1/documents/{document_id}`

- **Response `204`**; `404`

### 9.5 OCR — `/api/v1/ocr`

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| POST | `/api/v1/ocr/jobs` | User | OCR job 생성 |
| GET | `/api/v1/ocr/jobs` | User | 내 job 목록 |
| GET | `/api/v1/ocr/jobs/{job_id}` | User | job 상태 |
| GET | `/api/v1/ocr/jobs/{job_id}/results` | User | OCR 결과 |

#### POST `/api/v1/ocr/jobs`

- **Body:** `{ "document_id": uuid, "options"?: { "lang"?: string, "preprocess"?: { "deskew"?: bool, "denoise"?: bool, "contrast"?: bool } } }`
- **Response `202`:** `{ "id", "document_id", "status": "queued", "created_at" }`
- **Errors:** `404` document; `409` document not ready; `422` pages exceed

#### GET `/api/v1/ocr/jobs`

- **Query:** pagination, `status`
- **Response:** Page[OcrJobRead]

#### GET `/api/v1/ocr/jobs/{job_id}`

- **Response:** `{ id, document_id, status, error, options, started_at, finished_at, created_at }`
- **status enum:** `queued` \| `running` \| `succeeded` \| `failed` \| `cancelled`

#### GET `/api/v1/ocr/jobs/{job_id}/results`

- **Response:** `{ "job_id", "pages": [ { "page", "text", "boxes", "confidence" } ] }`
- **Errors:** `409` if not succeeded

### 9.6 AI — `/api/v1/ai`

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| POST | `/api/v1/ai/chat` | User | Chat completion |
| POST | `/api/v1/ai/vision` | User | Vision analysis |
| GET | `/api/v1/ai/prompts` | User | 프롬프트 목록 |
| GET | `/api/v1/ai/prompts/{prompt_id}` | User | 프롬프트 상세 |
| POST | `/api/v1/ai/prompts` | Admin | 생성 |
| PATCH | `/api/v1/ai/prompts/{prompt_id}` | Admin | 수정/새 버전 |
| POST | `/api/v1/ai/prompts/{prompt_id}/activate` | Admin | active 지정 |

#### POST `/api/v1/ai/chat`

- **Body:** `{ "messages": [{"role":"system"|"user"|"assistant","content":string}], "prompt_name"?: string, "prompt_version"?: int, "provider"?: "openai"|"gemini", "model"?: string, "temperature"?: number, "max_tokens"?: number }`
- **Response `200`:** `{ "request_id", "provider", "model", "message": {"role":"assistant","content":string}, "usage": {"tokens_in","tokens_out","latency_ms","cost_estimate"} }`
- **Errors:** `502` provider; `429` rate; `400` invalid prompt vars

#### POST `/api/v1/ai/vision`

- **Body:** `{ "document_id"?: uuid, "ocr_job_id"?: uuid, "image_document_id"?: uuid, "prompt_name"?: string, "prompt_version"?: int, "instruction"?: string, "provider"?: ..., "model"?: ... }`
- **Constraint:** document 또는 ocr_job 중 최소 하나
- **Response `200`:** `{ request_id, provider, model, result: object|string, usage }`

#### Prompt CRUD

- **PromptRead:** `{ id, name, version, template, variables_schema, active, created_at }`
- **POST body:** `{ name, template, variables_schema?, activate?: bool }`
- **PATCH body:** `{ template?, variables_schema?, create_new_version?: bool }`

### 9.7 Pipelines — `/api/v1/pipelines`

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| POST | `/api/v1/pipelines/runs` | User | 파이프라인 시작 |
| GET | `/api/v1/pipelines/runs` | User | 목록 |
| GET | `/api/v1/pipelines/runs/{run_id}` | User | 상태·스테이지 |

#### POST `/api/v1/pipelines/runs`

- **Body:** `{ "document_id": uuid, "ocr_options"?: object, "ai"?: { "prompt_name": string, "provider"?: string } }`
- **Response `202`:** `{ id, status: "queued", document_id, created_at }`

#### GET `/api/v1/pipelines/runs/{run_id}`

- **Response:** `{ id, status, stages: [{ name, status, error?, output_ref? }], document_id, created_at, finished_at }`
- **stages names:** `preprocess`, `ocr`, `ai_analyze`, `persist`

### 9.8 Statistics — `/api/v1/stats`

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/api/v1/stats/daily` | User | 본인 일별 (admin: 전역 가능) |
| GET | `/api/v1/stats/monthly` | User | 월별 rollup |
| GET | `/api/v1/stats/summary` | User | KPI 요약 |

#### GET `/api/v1/stats/daily`

- **Query:** `from` (date), `to` (date), `metric?`, `scope=self|global` (global=admin only)
- **Response:** `{ "points": [ { "date", "metric", "value", "dimensions" } ] }`

#### Metrics (normative names)

- `ocr.jobs.count`
- `ocr.jobs.failed`
- `ocr.jobs.latency_ms.avg`
- `ai.requests.count`
- `ai.tokens.in`
- `ai.tokens.out`
- `ai.cost.estimate`
- `pipeline.runs.count`
- `auth.login.failed` (admin)

#### GET `/api/v1/stats/monthly`

- **Query:** `from_month` (YYYY-MM), `to_month`, `metric?`, `scope`
- **Response:** monthly points

#### GET `/api/v1/stats/summary`

- **Response:** `{ "ocr_jobs_today", "ai_requests_today", "tokens_today", "error_rate_today" }`

#### GET `/api/v1/stats/export` (P1)

- **Query:** same as daily + `format=csv`
- **Response:** `text/csv`

### 9.9 Admin — `/api/v1/admin`

모든 경로 **Auth: role=admin**.

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/v1/admin/users` | 사용자 페이지 목록 |
| GET | `/api/v1/admin/users/{user_id}` | 사용자 상세 |
| PATCH | `/api/v1/admin/users/{user_id}` | role/status/name |
| GET | `/api/v1/admin/usage` | AI usage 목록 |
| GET | `/api/v1/admin/ocr-history` | OCR jobs 전역 |
| GET | `/api/v1/admin/ocr-history/{job_id}` | OCR job+results |
| GET | `/api/v1/admin/audit-logs` | 감사 로그 |
| GET | `/api/v1/admin/dashboard` | 전역 KPI 묶음 |

#### GET `/api/v1/admin/users`

- **Query:** `q` (email/name), `status`, `role`, pagination
- **Response:** Page[UserAdminRead]

#### PATCH `/api/v1/admin/users/{user_id}`

- **Body:** `{ "role"?: "admin"|"user", "status"?: "active"|"inactive", "name"?: string }`
- **Side effect:** audit_log
- **Response:** UserAdminRead

#### GET `/api/v1/admin/usage`

- **Query:** `from`, `to`, `provider`, `user_id`, pagination
- **Response:** Page[AiUsageRead]

#### GET `/api/v1/admin/ocr-history`

- **Query:** filters + pagination
- **Response:** Page[OcrJobAdminRead]

#### GET `/api/v1/admin/audit-logs`

- **Query:** `actor_id`, `action`, `from`, `to`, pagination
- **Response:** Page[AuditLogRead]

#### GET `/api/v1/admin/dashboard`

- **Response:** `{ "users_total", "ocr_jobs_24h", "ai_requests_24h", "error_rate_24h", "top_users": [], "provider_breakdown": [] }`

### 9.10 HTTP Status Code Policy

| Code | When |
| --- | --- |
| 200 | OK |
| 201 | Created |
| 202 | Accepted (async) |
| 204 | No Content |
| 400 | Domain validation |
| 401 | Unauthenticated |
| 403 | Forbidden / CSRF |
| 404 | Not found |
| 409 | Conflict |
| 413 | Payload too large |
| 415 | Unsupported media |
| 422 | Pydantic validation |
| 429 | Rate limited |
| 500 | Unexpected |
| 502 | Upstream provider |
| 503 | Not ready |

### 9.11 OpenAPI

- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`
- 모든 위 엔드포인트·스키마 반영 필수 (PRD coverage ≥ 95%)

---

## 10. Database Design

### 10.1 Database Inventory

| Store | Role | Engine | Durability |
| --- | --- | --- | --- |
| **PostgreSQL** | System of Record | PostgreSQL 16+ | Durable volume |
| **Redis** | Ephemeral coordination | Redis 7+ | Best-effort (denylist/queue) |
| **Filesystem volume** | Binary objects | Bind/named volume | Durable with host backups |

### 10.2 PostgreSQL — Database & Schema

| Item | Value |
| --- | --- |
| Database name | `ai_saas` (configurable) |
| Schema | `public` (v1) |
| Charset/collation | UTF-8 |
| ORM | SQLAlchemy 2.x |
| Migrations | Alembic |

### 10.3 Conventions

- PK: `UUID` v4 (stored as UUID type)
- Timestamps: `created_at`, `updated_at` timestamptz UTC
- Soft delete: status enum where applicable (`documents.status=deleted`)
- Money/cost: `NUMERIC(18,6)`
- JSON: `JSONB`
- Enum: PostgreSQL ENUM or SQLAlchemy check — **normative: native ENUM via Alembic**

### 10.4 Table: `users`

| Column | Type | Constraints | Notes |
| --- | --- | --- | --- |
| id | UUID | PK | |
| email | VARCHAR(320) | UNIQUE NOT NULL | citext optional |
| password_hash | VARCHAR(255) | NOT NULL | |
| name | VARCHAR(120) | NOT NULL | |
| role | ENUM(`user`,`admin`) | NOT NULL DEFAULT `user` | |
| status | ENUM(`active`,`inactive`) | NOT NULL DEFAULT `active` | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

**Indexes:** unique(email); index(status); index(role)

### 10.5 Table: `permissions` (P1 runtime, v1 schema present)

| Column | Type | Constraints |
| --- | --- | --- |
| id | UUID | PK |
| code | VARCHAR(100) | UNIQUE NOT NULL |
| description | TEXT | NULL |
| created_at | TIMESTAMPTZ | NOT NULL |

### 10.6 Table: `role_permissions`

| Column | Type | Constraints |
| --- | --- | --- |
| id | UUID | PK |
| role | ENUM(`user`,`admin`) | NOT NULL |
| permission_id | UUID | FK permissions.id ON DELETE CASCADE |
| created_at | TIMESTAMPTZ | NOT NULL |

**Indexes:** unique(role, permission_id)

### 10.7 Table: `refresh_tokens`

| Column | Type | Constraints | Notes |
| --- | --- | --- | --- |
| id | UUID | PK | |
| user_id | UUID | FK users.id ON DELETE CASCADE | |
| token_hash | VARCHAR(128) | UNIQUE NOT NULL | sha256 of token |
| jti | UUID | UNIQUE NOT NULL | |
| expires_at | TIMESTAMPTZ | NOT NULL | |
| revoked_at | TIMESTAMPTZ | NULL | |
| replaced_by_id | UUID | NULL FK refresh_tokens.id | rotation chain |
| created_at | TIMESTAMPTZ | NOT NULL | |
| user_agent | VARCHAR(512) | NULL | |
| ip | VARCHAR(64) | NULL | |

**Indexes:** index(user_id); index(expires_at)

### 10.8 Table: `documents`

| Column | Type | Constraints | Notes |
| --- | --- | --- | --- |
| id | UUID | PK | |
| owner_id | UUID | FK users.id | |
| filename | VARCHAR(512) | NOT NULL | |
| mime_type | VARCHAR(128) | NOT NULL | |
| size_bytes | BIGINT | NOT NULL | |
| checksum_sha256 | CHAR(64) | NOT NULL | |
| storage_key | VARCHAR(1024) | NOT NULL | |
| page_count | INT | NULL | PDF |
| status | ENUM(`uploaded`,`processing`,`ready`,`deleted`,`failed`) | NOT NULL | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

**Indexes:** index(owner_id, created_at DESC); index(status)

### 10.9 Table: `ocr_jobs`

| Column | Type | Constraints |
| --- | --- | --- |
| id | UUID | PK |
| document_id | UUID | FK documents.id |
| user_id | UUID | FK users.id |
| status | ENUM(`queued`,`running`,`succeeded`,`failed`,`cancelled`) | NOT NULL |
| options | JSONB | NOT NULL DEFAULT `{}` |
| error | TEXT | NULL |
| attempt_count | INT | NOT NULL DEFAULT 0 |
| started_at | TIMESTAMPTZ | NULL |
| finished_at | TIMESTAMPTZ | NULL |
| created_at | TIMESTAMPTZ | NOT NULL |
| updated_at | TIMESTAMPTZ | NOT NULL |

**Indexes:** index(user_id, created_at DESC); index(status, created_at); index(document_id)

### 10.10 Table: `ocr_results`

| Column | Type | Constraints |
| --- | --- | --- |
| id | UUID | PK |
| job_id | UUID | FK ocr_jobs.id ON DELETE CASCADE |
| page | INT | NOT NULL |
| text | TEXT | NOT NULL |
| boxes | JSONB | NOT NULL DEFAULT `[]` |
| confidence | NUMERIC(5,4) | NULL |
| created_at | TIMESTAMPTZ | NOT NULL |

**Indexes:** unique(job_id, page)

### 10.11 Table: `ai_prompts`

| Column | Type | Constraints |
| --- | --- | --- |
| id | UUID | PK |
| name | VARCHAR(120) | NOT NULL |
| version | INT | NOT NULL |
| template | TEXT | NOT NULL |
| variables_schema | JSONB | NOT NULL DEFAULT `{}` |
| active | BOOLEAN | NOT NULL DEFAULT false |
| created_by | UUID | FK users.id NULL |
| created_at | TIMESTAMPTZ | NOT NULL |
| updated_at | TIMESTAMPTZ | NOT NULL |

**Indexes:** unique(name, version); partial unique(name) WHERE active=true (one active per name)

### 10.12 Table: `ai_requests`

| Column | Type | Constraints |
| --- | --- | --- |
| id | UUID | PK |
| user_id | UUID | FK users.id |
| provider | ENUM(`openai`,`gemini`) | NOT NULL |
| model | VARCHAR(120) | NOT NULL |
| prompt_id | UUID | FK ai_prompts.id NULL |
| request_type | ENUM(`chat`,`vision`,`pipeline`) | NOT NULL |
| input_ref | JSONB | NOT NULL DEFAULT `{}` |
| output_ref | JSONB | NULL |
| status | ENUM(`succeeded`,`failed`) | NOT NULL |
| error | TEXT | NULL |
| created_at | TIMESTAMPTZ | NOT NULL |

**Indexes:** index(user_id, created_at DESC); index(provider, created_at)

### 10.13 Table: `ai_usages`

| Column | Type | Constraints |
| --- | --- | --- |
| id | UUID | PK |
| request_id | UUID | UNIQUE FK ai_requests.id ON DELETE CASCADE |
| tokens_in | INT | NOT NULL DEFAULT 0 |
| tokens_out | INT | NOT NULL DEFAULT 0 |
| latency_ms | INT | NOT NULL |
| cost_estimate | NUMERIC(18,6) | NOT NULL DEFAULT 0 |
| created_at | TIMESTAMPTZ | NOT NULL |

**Indexes:** index(created_at)

### 10.14 Table: `pipeline_runs`

| Column | Type | Constraints |
| --- | --- | --- |
| id | UUID | PK |
| user_id | UUID | FK users.id |
| document_id | UUID | FK documents.id |
| status | ENUM(`queued`,`running`,`succeeded`,`failed`,`cancelled`) | NOT NULL |
| stages | JSONB | NOT NULL DEFAULT `[]` |
| ocr_job_id | UUID | FK ocr_jobs.id NULL |
| ai_request_id | UUID | FK ai_requests.id NULL |
| error | TEXT | NULL |
| created_at | TIMESTAMPTZ | NOT NULL |
| finished_at | TIMESTAMPTZ | NULL |
| updated_at | TIMESTAMPTZ | NOT NULL |

**Indexes:** index(user_id, created_at DESC); index(status)

### 10.15 Table: `audit_logs`

| Column | Type | Constraints |
| --- | --- | --- |
| id | UUID | PK |
| actor_id | UUID | FK users.id NULL |
| action | VARCHAR(100) | NOT NULL |
| resource_type | VARCHAR(100) | NOT NULL |
| resource_id | VARCHAR(64) | NULL |
| payload | JSONB | NOT NULL DEFAULT `{}` |
| ip | VARCHAR(64) | NULL |
| request_id | VARCHAR(64) | NULL |
| created_at | TIMESTAMPTZ | NOT NULL |

**Indexes:** index(created_at DESC); index(actor_id, created_at DESC); index(action)

### 10.16 Table: `stat_daily`

| Column | Type | Constraints |
| --- | --- | --- |
| id | UUID | PK |
| date | DATE | NOT NULL |
| metric | VARCHAR(100) | NOT NULL |
| user_id | UUID | NULL FK users.id | NULL = global |
| dimensions | JSONB | NOT NULL DEFAULT `{}` |
| value | NUMERIC(24,6) | NOT NULL |
| created_at | TIMESTAMPTZ | NOT NULL |
| updated_at | TIMESTAMPTZ | NOT NULL |

**Indexes:** unique(date, metric, user_id, (dimensions)) — practical approach: unique on `(date, metric, user_id, dimensions_hash)` with `dimensions_hash` generated column; or store dimensions canonical string. **Normative:** columns `date`, `metric`, `user_id`, `dim_key` (VARCHAR canonical), `value` with **UNIQUE(date, metric, user_id, dim_key)**.

Revised normative columns add:

| Column | Type | Notes |
| --- | --- | --- |
| dim_key | VARCHAR(256) | NOT NULL DEFAULT `''` | canonical dimension key |

### 10.17 Entity-Relationship Summary

```
users 1──* documents
users 1──* refresh_tokens
users 1──* ocr_jobs
users 1──* ai_requests
users 1──* pipeline_runs
users 1──* audit_logs
documents 1──* ocr_jobs
ocr_jobs 1──* ocr_results
ai_prompts 1──* ai_requests
ai_requests 1──1 ai_usages
pipeline_runs 0..1──ocr_jobs
pipeline_runs 0..1──ai_requests
permissions 1──* role_permissions
```

### 10.18 Alembic Migration Plan (Logical Order)

1. `0001_users_auth` — users, refresh_tokens  
2. `0002_rbac` — permissions, role_permissions + seed codes  
3. `0003_documents` — documents  
4. `0004_ocr` — ocr_jobs, ocr_results  
5. `0005_ai` — ai_prompts, ai_requests, ai_usages  
6. `0006_pipelines` — pipeline_runs  
7. `0007_audit_stats` — audit_logs, stat_daily  

### 10.19 Redis — Logical Databases / Keyspaces

단일 Redis DB index `0` (v1). Key prefix: `aisaas:`.

| Key Pattern | Type | TTL | Purpose |
| --- | --- | --- | --- |
| `aisaas:rl:login:{email_or_ip}` | STRING/counter | 15m | login rate limit |
| `aisaas:rl:api:{user_id}` | STRING/counter | 1m | general API rate (optional) |
| `aisaas:auth:deny:{jti}` | STRING | until access/refresh exp | denylist |
| `aisaas:csrf:{session}` | STRING | 1h | CSRF secret association |
| `aisaas:idempotency:{user}:{key}` | STRING | 24h | idempotent POST responses |
| `aisaas:cache:stats:{user}:{day}` | STRING/JSON | 5m | optional stats cache |
| ARQ keys | ARQ internal | — | job queue (`arq:*`) |

**Redis persistence policy:** AOF optional. Denylist loss ⇒ users re-auth. Queue loss ⇒ jobs may need re-enqueue from `queued` DB reconciliation worker.

### 10.20 Filesystem Layout (Storage Volume)

```
{STORAGE_PATH}/
  documents/
    {yyyy}/
      {mm}/
        {document_uuid}/
          original.bin
          derived/          # optional preprocessed pages
```

`documents.storage_key` 예: `documents/2026/07/{uuid}/original.bin`

---

## 11. Security Design

| Topic | Design |
| --- | --- |
| Transport | HTTPS non-local; local HTTP allowed |
| Access token | JWT HS256, short TTL, Bearer |
| Refresh | HttpOnly cookie, hashed at rest, rotation, reuse detection |
| CSRF | Double-submit for cookie-authenticated routes |
| Passwords | Argon2id |
| Secrets | env only |
| Upload | MIME allowlist + size + checksum |
| RBAC | admin vs user; service ownership checks |
| CORS | allowlist + credentials |
| Logging | no secrets/PII dumps |
| Provider keys | server-side only; never to FE |

---

## 12. Deployment Architecture

### 12.1 Compose Services

| Service | Build | Command | Ports | Volumes |
| --- | --- | --- | --- | --- |
| postgres | image | default | 5432 | pgdata |
| redis | image | default | 6379 | optional redisdata |
| api | backend Dockerfile | uvicorn | 8000 | storage |
| worker | same image | arq worker | — | storage |
| web | frontend Dockerfile | next start | 3000 | — |

### 12.2 Startup Order

1. postgres healthy  
2. redis healthy  
3. api (migrate on deploy job / entrypoint flag)  
4. worker  
5. web  

### 12.3 Scaling Knobs (without MSA)

- Replicate `api` behind reverse proxy  
- Replicate `worker` for OCR/AI throughput  
- Vertical scale postgres; Redis memory for queues  

---

## 13. Observability & Operations

| Signal | Mechanism |
| --- | --- |
| Logs | JSON stdout: level, request_id, user_id?, path, latency |
| Health | `/health`, `/ready` |
| Audit | `audit_logs` for admin mutations & auth anomalies |
| Usage | `ai_usages`, `ocr_jobs` |
| Stats | `stat_daily` + admin dashboard API |

---

## 14. Error & Exception Mapping

| Exception Class | HTTP | code |
| --- | --- | --- |
| ValidationError (Pydantic) | 422 | `validation_error` |
| UnauthorizedError | 401 | `unauthorized` |
| ForbiddenError | 403 | `forbidden` |
| NotFoundError | 404 | `not_found` |
| ConflictError | 409 | `conflict` |
| RateLimitError | 429 | `rate_limited` |
| ProviderTimeoutError | 502 | `provider_timeout` |
| ProviderError | 502 | `provider_error` |
| AppError (generic) | 400/500 | `app_error` |

---

## 15. Frontend Architecture Notes

- Route groups: `(auth)`, `(app)`, `(admin)` with role guards  
- Polling interval for jobs: 1–2s backoff to 5s  
- Charts consume `/stats/*` only  
- No business logic in components beyond presentation state  
- All network via `frontend/services/*`  

---

## 16. Traceability Matrix (PRD → SDS)

| PRD Area | SDS Section |
| --- | --- |
| Goals / Non-Goals | ADR-001, ADR-016, ADR-017 |
| Stack | ADR-004–014, §6 |
| Layers / MVC | §4, ADR-003 |
| Features Auth→Admin | §7, §8, §9 |
| Data model | §10 |
| API catalogue | §9 |
| Docker | §12, ADR-017 |
| Open Questions | Resolved in ADR-008,010,014,015,016,011,012 |

---

## 17. Implementation Gate Checklist

구현 착수 전 SDS 준수 확인:

- [ ] 모든 ADR Accepted 유지  
- [ ] 폴더 트리 생성 계획이 SDS §5와 일치  
- [ ] 계층 import 규칙 문서화(리뷰 체크리스트)  
- [ ] Alembic 초기 리비전 계획 §10.18  
- [ ] OpenAPI에 §9 엔드포인트 반영 계획  
- [ ] Compose 서비스 5종  
- [ ] 코드 작성 없음(본 문서 단계) → 다음 단계에서만 코드  

---

## 18. Document History

| Version | Date | Author | Changes |
| --- | --- | --- | --- |
| 1.0.0 | 2026-07-18 | Architecture | Initial SDS from PRD v1.0.0; all ADRs decided |

---

## 19. Summary

본 SDS는 AI SaaS Framework의 **전 아키텍처 결정(ADR-001~032), 전 폴더 책임, 전 계층 규칙, 전 의존성, 전 모듈 경계, 전 v1 API, PostgreSQL·Redis·Filesystem 전 저장소 설계**를 규범으로 고정한다.

상위 계약은 PRD이며, 구현은 본 SDS를 위반하지 않는 범위에서만 진행한다. **소스 코드는 본 문서에 포함하지 않는다.**
