# Product Requirements Document (PRD)

| Field | Value |
| --- | --- |
| **Product Name** | AI SaaS Framework (AI Starter Framework) |
| **Document Type** | Product Requirements Document |
| **Version** | 1.0.0 |
| **Status** | Draft — Ready for Engineering Spec |
| **Last Updated** | 2026-07-18 |
| **Owner** | Product / Architecture |
| **Audience** | Engineering, Design, QA, DevOps, Stakeholders |
| **Related Docs** | Architecture Spec, API Spec, Data Model Spec, Security Spec (to follow) |

---

## 1. Executive Summary

AI SaaS Framework는 OCR, 문서 분석, AI 챗봇/비전, 통계·대시보드, 관리자 기능을 **재사용 가능한 운영형 모놀리식 SaaS 기반**으로 제공하는 프레임워크이다.

목표는 “데모용 예제”가 아니라, 팀이 Clone 후 즉시 도메인 기능을 붙여 **실제 서비스로 배포·운영**할 수 있는 표준 골격이다. Frontend(Next.js)와 Backend(FastAPI)는 API로 완전 분리되며, PostgreSQL·Redis·Docker를 기본 런타임으로 삼는다. 애플리케이션 계층은 **MVC + Service + Repository Pattern**을 강제하여 유지보수성과 확장성을 확보한다.

**한 줄 가치 제안:**  
*“OCR → 전처리 → AI 분석 → 저장 → 통계 → 대시보드” 파이프라인을 처음부터 다시 짓지 않고, 검증된 SaaS 골격 위에서 제품화한다.*

---

## 2. Problem Statement

### 2.1 Pain Points

| # | Problem | Impact |
| --- | --- | --- |
| P1 | AI/OCR SaaS를 프로젝트마다 처음부터 구성 | 착수 지연, 보안·인증·인프라 반복 실수 |
| P2 | 컨트롤러에 비즈니스 로직이 섞인 구조 | 테스트 불가, 기능 추가 시 회귀 비용 증가 |
| P3 | Frontend/Backend 결합 또는 문서화되지 않은 API | 병렬 개발 불가, 클라이언트 교체 비용 |
| P4 | OCR·LLM 제공자(OpenAI/Gemini 등) 하드코딩 | 벤더 락인, 비용·품질 A/B 불가 |
| P5 | 개발/운영 환경 불일치 | “로컬에서는 되는데” 장애, 온보딩 비용 |
| P6 | 사용량·이력·권한 부재 | 과금·감사·운영 불가 |

### 2.2 Opportunity

표준 인증(JWT), 계층형 백엔드, Docker Compose 일원화, OCR/AI 어댑터, 관리자·통계 모듈을 **프레임워크 기본 제공**하면, 도메인 팀은 제품 차별화에만 집중할 수 있다.

---

## 3. Product Vision & Goals

### 3.1 Vision

실무에서 바로 쓸 수 있는 **AI First · API First · Docker First** SaaS Framework.

### 3.2 Product Goals

| ID | Goal | Success Signal |
| --- | --- | --- |
| G1 | 재사용 가능한 Framework | Clone 후 환경변수·Compose만으로 로컬 기동 |
| G2 | 유지보수 우선 구조 | Controller에 비즈니스 로직 0건 (리뷰 게이트) |
| G3 | AI First 파이프라인 | OCR→AI→DB→Stats→Dashboard E2E 시나리오 동작 |
| G4 | API First | Swagger/OpenAPI로 Backend 단독 검증 가능 |
| G5 | Docker First | 개발·스테이징·운영이 동일 Compose 계열 이미지 |
| G6 | 확장 가능한 모놀리스 | 모듈 추가 시 기존 모듈 변경 최소화 |

### 3.3 Non-Goals (v1)

다음 항목은 **v1 범위에서 명시적으로 제외**한다. 필요 시 이후 메이저 버전에서 재검토한다.

- Microservices Architecture (MSA)
- Kubernetes 기반 오케스트레이션
- Event Sourcing
- CQRS
- 멀티 테넌시 완전 격리(스키마/DB per tenant) — v1은 단일 테넌트 또는 soft isolation(org_id) 수준만 허용
- 실시간 협업 에디터, 복잡한 워크플로 엔진

---

## 4. Target Users & Personas

| Persona | Role | Needs | Primary Surfaces |
| --- | --- | --- | --- |
| **Framework Consumer Dev** | Python/TS 개발자 | Clone·실행·모듈 확장 가이드 | Docs, API, Docker |
| **AI/OCR Engineer** | 모델·파이프라인 | Provider 교체, 프롬프트·전처리 튜닝 | AI/OCR services |
| **Product Admin** | 운영 관리자 | 사용자·권한·사용량·로그 | Admin Dashboard |
| **End User** | SaaS 최종 사용자 | 업로드, OCR, AI 질의, 리포트 | Web App |
| **Data Analyst** | 분석가 | 일/월 통계, 차트 export | Statistics Dashboard |
| **Laravel/Node 전환 개발자** | 타 스택 출신 | MVC·Repository와 유사한 명확한 계층 | Backend layout |

---

## 5. Scope

### 5.1 In Scope (v1)

1. 사용자 인증·인가 (JWT Access + Refresh, Role/Permission)
2. 사용자/조직(또는 워크스페이스) 기본 CRUD
3. 이미지·PDF 업로드 및 PaddleOCR 기반 OCR
4. OpenCV 기반 이미지 전처리(향상)
5. OpenAI / Gemini LLM·Vision 어댑터 및 프롬프트 관리
6. 문서 메타·추출 텍스트 저장 및 조회
7. AI/OCR 사용량·이력 추적
8. 통계 API 및 Dashboard UI (일/월, 차트)
9. Admin: 사용자, AI Usage, OCR History, Logs
10. PostgreSQL + SQLAlchemy + Alembic
11. Redis (캐시, Rate Limit, Refresh/Session 보조, 작업 큐 브로커)
12. Docker Compose 기반 로컬/배포 골격
13. Next.js 관리·사용자 UI (App Router)
14. OpenAPI(Swagger) 문서 자동 노출

### 5.2 Out of Scope (v1)

- 고가용성 멀티 리전 액티브-액티브
- 완전 자동 과금/결제 게이트웨이 (사용량 계측만)
- 온프레미스 에어갭 전용 배포 패키지 (Docker로 대체 가능 수준만)
- 네이티브 모바일 앱
- 고급 RAG(벡터 DB 클러스터, hybrid search 고도화) — **기본 RAG 훅/인터페이스는 v1.1 후보**

### 5.3 Future Candidates (Post-v1)

| Phase | Candidate |
| --- | --- |
| v1.1 | RAG (임베딩 저장, 검색, 인용), Ollama 로컬 LLM |
| v1.2 | Soft multi-tenant (org quota, branding) |
| v2.0 | Worker 분리 스케일아웃, 선택적 서비스 분리 |
| Later | K8s Helm, Event-driven 파이프라인 |

---

## 6. Success Metrics (KPIs)

| Metric | Definition | v1 Target |
| --- | --- | --- |
| Time-to-First-API | Clone → `docker compose up` → health OK | ≤ 30 minutes |
| Auth Completeness | Login / Refresh / Role guard E2E | 100% core flows |
| OCR Pipeline SLA (dev) | 단일 페이지 이미지 OCR p95 | ≤ 15s (CPU baseline) |
| AI Provider Switch | Config만으로 OpenAI↔Gemini 전환 | 코드 변경 0 |
| Layer Violations | Controller→DB 직접 접근 | 0 (CI/lint 정책) |
| API Document Coverage | Public routes in OpenAPI | ≥ 95% |
| Scale Readiness | 설계상 지원 사용자 | 100 → 10k → 100k+ (단계적) |

---

## 7. Assumptions & Constraints

### 7.1 Assumptions

- 초기 배포는 단일 리전, 단일 Compose/호스트 또는 소규모 VM 클러스터
- LLM API 키는 운영자가 환경변수로 주입
- OCR은 CPU 기본, GPU는 옵션
- UI는 데스크톱 브라우저 우선, 반응형은 필수이나 모바일 네이티브 UX는 비목표
- 문서는 Spec → Implementation → Test → Docs 순서를 따른다

### 7.2 Constraints

| Area | Constraint |
| --- | --- |
| Architecture | 모듈형 모놀리스 (MSA 금지, v1) |
| Backend | Python + FastAPI |
| Frontend | TypeScript + Next.js |
| Persistence | PostgreSQL only (primary) |
| Cache/Queue | Redis |
| ORM/Migrations | SQLAlchemy + Alembic |
| Auth | JWT (stateless access + refresh strategy) |
| Patterns | MVC + Repository + Service; 의존성 단방향 |
| Packaging | Docker / Docker Compose |

---

## 8. Technology Stack (Normative)

| Layer | Technology | Role |
| --- | --- | --- |
| API Framework | **FastAPI** | REST API, OpenAPI, DI, async endpoints |
| Web UI | **Next.js** | App Router, SSR/CSR, Admin & User UX |
| RDBMS | **PostgreSQL** | 트랜잭션 데이터, 이력, 권한 |
| Cache / Broker | **Redis** | 캐시, rate limiting, refresh denylist/session, job queue |
| ORM | **SQLAlchemy** | 모델·세션·쿼리 추상화 |
| Migrations | **Alembic** | 스키마 버전 관리 |
| OCR | **PaddleOCR** | 텍스트 추출 |
| Image | OpenCV (supporting) | 전처리·향상 |
| LLM | **OpenAI**, **Gemini** | Chat / Vision / Analysis |
| Auth | **JWT** | Access + Refresh |
| Packaging | **Docker**, Docker Compose | 환경 일관성 |
| Architecture | **MVC + Repository Pattern** | 계층 분리 |

### 8.1 Stack Rationale (요약)

- FastAPI: 자동 OpenAPI, 타입 힌트, 비동기 I/O로 AI/OCR 대기 작업에 적합
- Next.js: API First UI, 관리자·대시보드에 적합
- PostgreSQL: 관계형 권한·이력·리포트에 적합
- Redis: LLM/OCR 비용 보호(rate limit), 짧은 TTL 캐시, 백그라운드 작업
- SQLAlchemy + Alembic: 운영 마이그레이션 표준
- PaddleOCR: 다국어·오프라인 친화 OCR 엔진
- OpenAI/Gemini: 상용 품질 LLM 이중화로 벤더 리스크 완화
- JWT: 수평 확장 친화 무상태 Access Token
- Docker: 개발=운영 원칙 강제

---

## 9. System Architecture

### 9.1 Logical Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Next.js (Presentation)                  │
│         App Router · Components · Hooks · Client SDK        │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTPS / REST (JWT)
┌───────────────────────────▼─────────────────────────────────┐
│                    FastAPI (Controllers/Routers)            │
│              Auth Middleware · Validation · OpenAPI         │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                         Services                            │
│     Auth · User · OCR · AI · Document · Stats · Admin       │
└───────────────┬─────────────────────────────┬───────────────┘
                │                             │
┌───────────────▼───────────┐   ┌─────────────▼───────────────┐
│       Repositories        │   │   External Adapters         │
│   SQLAlchemy Session      │   │  OpenAI · Gemini · OCR      │
└───────────────┬───────────┘   │  Object Storage (files)     │
                │               └─────────────────────────────┘
┌───────────────▼───────────┐   ┌─────────────────────────────┐
│       PostgreSQL          │   │           Redis             │
└───────────────────────────┘   └─────────────────────────────┘
                ▲
                │ (async jobs)
┌───────────────┴─────────────────────────────────────────────┐
│                     Workers (optional queue)                │
│              OCR jobs · AI batch · report generation        │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 Layer Rules (Normative)

| Layer | Responsibility | Must Not |
| --- | --- | --- |
| **Controller (Router)** | HTTP, status code, DTO(schema) 입·출력 | Business rules, SQL, provider SDK 직접 호출 |
| **Service** | Use-case / business logic, orchestration | HTTP 세부사항, raw SQL 산재 |
| **Repository** | Persistence CRUD/query | AI/OCR 호출, HTTP |
| **Model** | ORM entity | API schema 겸용 금지(권장) |
| **Schema (DTO)** | Request/Response validation | DB session 보유 |
| **Adapter/Client** | OpenAI, Gemini, PaddleOCR, Storage | Domain policy 소유 |
| **Worker** | Long-running jobs | UI 렌더링 |

**Dependency Direction (강제):**  
`Controller → Service → Repository → Database`  
역참조 및 Controller → Repository 우회는 **금지**.

### 9.3 MVC Mapping

| MVC | Framework Mapping |
| --- | --- |
| Model | SQLAlchemy models + domain entities |
| View | Next.js pages/components (및 API JSON as machine view) |
| Controller | FastAPI routers |

Repository/Service는 MVC를 Clean Architecture 방향으로 확장한 운영 패턴이다.

---

## 10. Repository Layout (Target)

```
backend/
  app/
    core/           # settings, security, db, redis, deps
    routers/        # Controllers
    services/
    repositories/
    models/
    schemas/
    middleware/
    exceptions/
    utils/
    workers/
    tests/
  alembic/
frontend/
  app/
  components/
  hooks/
  lib/
  services/
  types/
  public/
docker/
scripts/
docs/
.github/
docker-compose.yml
.env.example
README.md
```

---

## 11. Functional Requirements

우선순위: **P0** = v1 Must, **P1** = Should, **P2** = Could

### 11.1 Authentication & Authorization

| ID | Requirement | Priority | Acceptance Criteria |
| --- | --- | --- | --- |
| AUTH-01 | 이메일/비밀번호 로그인 | P0 | 유효 자격증명 → Access+Refresh JWT 발급 |
| AUTH-02 | Access Token (JWT) | P0 | 만료·서명 검증, Bearer 헤더 |
| AUTH-03 | Refresh Token 회전 | P0 | Refresh로 Access 재발급; 재사용 탐지 시 무효화 가능 |
| AUTH-04 | 로그아웃 | P0 | Refresh 무효화(Redis denylist 또는 DB revoke) |
| AUTH-05 | Role 기반 접근 | P0 | `admin`, `user` 최소 역할; 라우트 가드 |
| AUTH-06 | Permission 세분화 | P1 | resource:action 권한 매트릭스 |
| AUTH-07 | 비밀번호 해싱 | P0 | 현대적 KDF (예: bcrypt/argon2); 평문 저장 금지 |
| AUTH-08 | Rate limit on auth | P0 | Redis 기반 로그인 시도 제한 |

### 11.2 User Management

| ID | Requirement | Priority | Acceptance Criteria |
| --- | --- | --- | --- |
| USER-01 | 회원가입/초대 | P0 | 중복 이메일 거부, 기본 role 부여 |
| USER-02 | 프로필 조회/수정 | P0 | 본인만 수정; admin은 대리 가능 |
| USER-03 | 사용자 목록(Admin) | P0 | 페이지네이션, 검색, 상태 필터 |
| USER-04 | 활성화/비활성화 | P0 | 비활성 사용자는 API 거부 |

### 11.3 File Upload & Document

| ID | Requirement | Priority | Acceptance Criteria |
| --- | --- | --- | --- |
| DOC-01 | 이미지 업로드 | P0 | jpg/png/webp; 크기·MIME 검증 |
| DOC-02 | PDF 업로드 | P0 | PDF; 페이지 수 제한 설정 가능 |
| DOC-03 | 문서 메타 저장 | P0 | owner, type, size, checksum, status |
| DOC-04 | Word/Excel/Text | P1 | 텍스트 추출 파이프라인 훅 |
| DOC-05 | 파일 스토리지 추상화 | P0 | 로컬 볼륨 기본; S3 호환 인터페이스 예약 |

### 11.4 OCR

| ID | Requirement | Priority | Acceptance Criteria |
| --- | --- | --- | --- |
| OCR-01 | PaddleOCR 엔진 연동 | P0 | 이미지에서 텍스트+bbox 추출 |
| OCR-02 | PDF 페이지 OCR | P0 | 페이지별 job 결과 저장 |
| OCR-03 | OpenCV 전처리 | P0 | deskew/denoise/contrast 옵션 |
| OCR-04 | 비동기 Job | P0 | Redis 큐 → Worker; 상태 `queued/running/succeeded/failed` |
| OCR-05 | OCR History | P0 | 사용자·admin 조회, 재실행(P1) |
| OCR-06 | 다국어 설정 | P1 | 언어 파라미터로 엔진 설정 |

### 11.5 AI (OpenAI / Gemini)

| ID | Requirement | Priority | Acceptance Criteria |
| --- | --- | --- | --- |
| AI-01 | Provider 추상화 | P0 | 동일 Service 인터페이스로 OpenAI/Gemini 호출 |
| AI-02 | Chat Completion | P0 | 메시지 히스토리, temperature 등 기본 파라미터 |
| AI-03 | Vision Analysis | P0 | 이미지/OCR 결과 기반 구조화 분석 |
| AI-04 | Prompt Management | P0 | 이름·버전·템플릿 변수 저장/적용 |
| AI-05 | Usage Metering | P0 | tokens/cost estimate/provider별 로그 |
| AI-06 | Fallback Provider | P1 | Primary 실패 시 Secondary 전환 정책 |
| AI-07 | Streaming 응답 | P1 | SSE/WebStream (Chat) |
| AI-08 | Ollama (local) | P2 | v1.1 후보; 인터페이스만 예약 가능 |

### 11.6 AI-First Pipeline (Core Journey)

| ID | Requirement | Priority | Acceptance Criteria |
| --- | --- | --- | --- |
| PIPE-01 | Upload → Preprocess → OCR → AI → Persist | P0 | 단일 API 오케스트레이션 또는 명시적 단계 API |
| PIPE-02 | Pipeline 상태 추적 | P0 | 단계별 status/error 기록 |
| PIPE-03 | 결과 구조화 저장 | P0 | JSON schema 버전 필드 포함 |
| PIPE-04 | Statistics 반영 | P0 | 성공/실패/지연 지표 집계 가능 |

### 11.7 Statistics & Dashboard

| ID | Requirement | Priority | Acceptance Criteria |
| --- | --- | --- | --- |
| STAT-01 | Daily / Monthly aggregates | P0 | OCR jobs, AI calls, tokens, errors |
| STAT-02 | Chart-ready API | P0 | time-series JSON |
| STAT-03 | User Dashboard UI | P0 | 본인 사용량·최근 작업 |
| STAT-04 | Admin Dashboard UI | P0 | 전역 KPI, Top users, error rate |
| STAT-05 | Export CSV | P1 | 기간 필터 export |

### 11.8 Admin & Observability

| ID | Requirement | Priority | Acceptance Criteria |
| --- | --- | --- | --- |
| ADM-01 | User management UI/API | P0 | CRUD + role |
| ADM-02 | AI Usage viewer | P0 | provider/model/cost/time |
| ADM-03 | OCR History viewer | P0 | input preview meta + result |
| ADM-04 | Application logs (ops) | P1 | request-id 상관관계 |
| ADM-05 | Health / Readiness | P0 | DB/Redis 의존성 체크 |

### 11.9 Frontend (Next.js)

| ID | Requirement | Priority | Acceptance Criteria |
| --- | --- | --- | --- |
| FE-01 | Auth pages (login/logout) | P0 | 토큰 안전 저장 전략 문서화(HttpOnly cookie 권장) |
| FE-02 | Upload & OCR console | P0 | 진행상태 폴링/구독 |
| FE-03 | AI chat/analysis UI | P0 | provider 선택(권한 있는 경우) |
| FE-04 | Stats dashboard | P0 | 차트 컴포넌트 |
| FE-05 | Admin console | P0 | role=admin만 접근 |
| FE-06 | API client layer | P0 | typed client; UI에서 raw fetch 산재 금지(가이드) |

---

## 12. Non-Functional Requirements

### 12.1 Performance

| ID | Requirement |
| --- | --- |
| NFR-P01 | API(비 AI) p95 < 300ms (로컬/소규모 배포, warm) |
| NFR-P02 | 동기 OCR은 소용량만; 대용량은 비동기 Job 필수 |
| NFR-P03 | DB 인덱스: user email unique, job status+created_at, usage created_at |

### 12.2 Scalability

| ID | Requirement |
| --- | --- |
| NFR-S01 | Stateless API 인스턴스 수평 확장 가능 (JWT + Redis 공유) |
| NFR-S02 | Worker 복제로 OCR/AI 처리량 확장 |
| NFR-S03 | 설계 목표: 100 → 10,000 → 100,000+ users (단계적 용량 계획) |

### 12.3 Reliability

| ID | Requirement |
| --- | --- |
| NFR-R01 | Job 실패 시 재시도 정책(최대 N회, exponential backoff) |
| NFR-R02 | Provider timeout/circuit 정책 |
| NFR-R03 | Alembic으로 롤링 배포 시 하위호환 마이그레이션 원칙 |

### 12.4 Security

| ID | Requirement |
| --- | --- |
| NFR-SEC01 | 모든 비밀값은 환경변수/시크릿; 리포지토리 커밋 금지 |
| NFR-SEC02 | JWT 비밀키 강도·교체 절차 문서화 |
| NFR-SEC03 | Upload MIME/size/malware 기본 가드(확장자+content-type+크기) |
| NFR-SEC04 | RBAC on every mutating admin route |
| NFR-SEC05 | CORS allowlist |
| NFR-SEC06 | PII 최소화; 로그에 비밀번호·토큰·API key 금지 |
| NFR-SEC07 | HTTPS only in non-local environments |

### 12.5 Observability

| ID | Requirement |
| --- | --- |
| NFR-O01 | Structured logging (JSON 권장) + request_id |
| NFR-O02 | Health, readiness endpoints |
| NFR-O03 | AI/OCR usage metrics 영속화 |

### 12.6 Maintainability & Quality

| ID | Requirement |
| --- | --- |
| NFR-M01 | SOLID, DRY, KISS, Clean Architecture 원칙 준수 |
| NFR-M02 | Layer lint/리뷰 체크리스트 |
| NFR-M03 | Backend unit(service) + API integration tests |
| NFR-M04 | Spec 없는 기능 구현 금지 (Documentation Policy) |

### 12.7 Usability / DX

| ID | Requirement |
| --- | --- |
| NFR-DX01 | `.env.example` 완비 |
| NFR-DX02 | `docker compose up` 원커맨드 기동 |
| NFR-DX03 | Swagger UI 기본 제공 |
| NFR-DX04 | README: 아키텍처, 기동, 모듈 추가 가이드 |

---

## 13. Conceptual Data Model

> 논리 모델이다. 물리 스키마는 Data Model Spec / Alembic으로 확정한다.

### 13.1 Core Entities

| Entity | Key Attributes | Notes |
| --- | --- | --- |
| **User** | id, email, password_hash, role, status, timestamps | unique email |
| **Permission** (opt) | id, code, description | P1 |
| **RolePermission** | role, permission_id | P1 |
| **RefreshToken** | id, user_id, jti/hash, expires_at, revoked_at | Redis denylist와 병행 가능 |
| **Document** | id, owner_id, filename, mime, size, storage_key, checksum, status | |
| **OcrJob** | id, document_id, status, options_json, error, started_at, finished_at | |
| **OcrResult** | id, job_id, page, text, boxes_json, confidence | |
| **AiPrompt** | id, name, version, template, variables_schema, active | |
| **AiRequest** | id, user_id, provider, model, prompt_id, input_ref, status | |
| **AiUsage** | id, request_id, tokens_in/out, latency_ms, cost_estimate | |
| **PipelineRun** | id, user_id, document_id, stages_json, status | |
| **AuditLog** | id, actor_id, action, resource, payload, created_at | Admin |
| **StatDaily** | date, metric, dimensions, value | materialize or view |

### 13.2 Key Relationships

- User 1—* Document / OcrJob / AiRequest
- Document 1—* OcrJob 1—* OcrResult
- AiPrompt 1—* AiRequest 1—1 AiUsage
- PipelineRun references Document + stage outputs

---

## 14. API Design Principles

### 14.1 Conventions

- Base path: `/api/v1`
- Resource-oriented REST
- JSON request/response
- Pagination: `page`, `page_size` (또는 cursor for large logs)
- Errors: 표준 에러 envelope (`code`, `message`, `details`, `request_id`)
- Auth: `Authorization: Bearer <access_token>`
- Idempotency: 업로드/결제성 작업에 `Idempotency-Key` (P1)

### 14.2 Endpoint Groups (v1 Catalogue)

| Group | Examples | Auth |
| --- | --- | --- |
| Health | `GET /health`, `GET /ready` | Public |
| Auth | `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout` | Mixed |
| Users | `GET/PATCH /users/me`, Admin `GET /admin/users` | User/Admin |
| Documents | `POST /documents`, `GET /documents/{id}` | User |
| OCR | `POST /ocr/jobs`, `GET /ocr/jobs/{id}` | User |
| AI | `POST /ai/chat`, `POST /ai/vision`, `CRUD /ai/prompts` | User/Admin |
| Pipelines | `POST /pipelines/runs`, `GET /pipelines/runs/{id}` | User |
| Stats | `GET /stats/daily`, `GET /stats/monthly` | User/Admin scoped |
| Admin | usage, ocr history, audit | Admin |

> 상세 필드·스키마는 OpenAPI Spec 문서에서 확정한다. 본 PRD는 제품 계약을 정의한다.

### 14.3 OpenAPI

- FastAPI 자동 생성 Swagger/ReDoc 필수
- Breaking change는 `/api/v2` 또는 호환 필드 전략으로 관리

---

## 15. Authentication & Session Design

### 15.1 Token Model

| Token | Lifetime (default) | Storage | Purpose |
| --- | --- | --- | --- |
| Access JWT | 15–60 minutes | Memory / short-lived client store | API 인가 |
| Refresh Token | days–weeks | HttpOnly Secure Cookie 권장 또는 보안 저장소 | Access 재발급 |

### 15.2 Claims (최소)

- `sub` (user id)
- `role` (또는 roles)
- `jti`
- `iat`, `exp`
- 선택: `permissions` (짧을 때만; 길면 DB/Redis lookup)

### 15.3 Redis Roles in Auth

- Login rate limiting
- Refresh token denylist / rotation tracking
- Optional session metadata

### 15.4 Authorization Model

1. **Role**: `admin`, `user` (v1 최소)
2. **Permission** (P1): 예) `ocr:run`, `ai:manage_prompts`, `admin:users`
3. Router dependency에서 검증; Service에서도 민감 연산 재확인(Defense in depth)

---

## 16. OCR & AI Processing Design

### 16.1 OCR Flow

```
Client Upload → Document persist (storage + DB)
     → Enqueue OcrJob (Redis)
     → Worker: OpenCV preprocess → PaddleOCR
     → Persist OcrResult
     → Optional: trigger AI analysis
     → Notify via status API (poll; webhook P2)
```

### 16.2 AI Flow

```
Client request (chat/vision/pipeline)
     → Resolve Prompt template + variables
     → Select Provider (config / request / policy)
     → Call OpenAI or Gemini adapter
     → Persist AiRequest + AiUsage
     → Return structured response
```

### 16.3 Provider Adapter Contract

모든 LLM 어댑터는 동일 인터페이스를 구현한다.

- `chat(messages, params) -> ChatResult`
- `vision(images, prompt, params) -> VisionResult`
- `health() -> bool`
- 에러는 도메인 예외로 매핑 (timeout, rate_limit, auth, invalid_request)

설정 예: `AI_PRIMARY_PROVIDER=openai`, `AI_FALLBACK_PROVIDER=gemini`

---

## 17. Redis Usage Matrix

| Use Case | Pattern | TTL / Notes |
| --- | --- | --- |
| Auth rate limit | counters / sliding window | short |
| Refresh revoke | denylist by jti | until token exp |
| Response cache | optional GET caches | short; user-scoped keys |
| Job queue | list/streams or broker lib | workers consume |
| Distributed locks | optional job dedupe | short |

PostgreSQL이 SoR(System of Record)이며, Redis는 휘발·가속·조정 용도이다.

---

## 18. Docker & Deployment

### 18.1 Compose Services (v1)

| Service | Image/Build | Depends On |
| --- | --- | --- |
| `api` | backend Dockerfile | postgres, redis |
| `worker` | same image, worker cmd | postgres, redis |
| `web` | frontend Dockerfile | api |
| `postgres` | official PostgreSQL | — |
| `redis` | official Redis | — |

### 18.2 Environment Contract

`.env.example`에 최소 포함:

- `DATABASE_URL`
- `REDIS_URL`
- `JWT_SECRET` / `JWT_ALGORITHM` / token TTLs
- `OPENAI_API_KEY`
- `GEMINI_API_KEY`
- `AI_PRIMARY_PROVIDER`
- `STORAGE_PATH` or object storage creds
- `CORS_ORIGINS`
- `APP_ENV` (`local|staging|production`)

### 18.3 Deployment Principles

- 개발과 운영은 동일 이미지 계열
- 마이그레이션은 배포 파이프라인에서 `alembic upgrade head`
- K8s는 Non-Goal; 추후 별도 트랙

---

## 19. Development Strategy & Phased Roadmap

문서화된 개발 순서(규범):

| Phase | Focus | Exit Criteria |
| --- | --- | --- |
| **0. Foundation** | Repo layout, Docker, settings, DB, Redis, health | Compose up green |
| **1. Authentication** | JWT login/refresh/roles | Auth E2E + Swagger |
| **2. User** | profile + admin users | RBAC smoke |
| **3. OCR** | upload, preprocess, PaddleOCR jobs | OCR history |
| **4. AI** | OpenAI/Gemini adapters, prompts, usage | provider switch |
| **5. Statistics** | aggregates + APIs | daily/monthly |
| **6. Dashboard** | Next.js charts/consoles | user+admin UX |
| **7. Admin** | usage, logs, OCR history UI | admin acceptance |
| **8. Deployment** | staging compose, CI basics, hardening | production checklist |

### 19.1 Documentation Policy (규범)

```
Specification → Implementation → Test → Documentation
```

기능은 스펙 없이 구현하지 않는다.

---

## 20. Quality Assurance & Acceptance

### 20.1 Test Pyramid

| Level | Scope |
| --- | --- |
| Unit | Services, adapters (mocked providers) |
| Integration | Repository + PostgreSQL, Redis |
| API | FastAPI TestClient / httpx; auth flows |
| E2E (smoke) | Compose stack: login → upload → OCR job → stats |
| Contract | OpenAPI schema validation (CI) |

### 20.2 Definition of Done (Feature)

- Spec 승인
- Layer 규칙 준수 (PR 체크리스트)
- 테스트 통과
- OpenAPI 반영
- 마이그레이션 포함(스키마 변경 시)
- README/모듈 문서 업데이트
- Security 민감 설정 점검

### 20.3 v1 Product Acceptance (Release Gate)

1. Compose로 전체 스택 기동
2. 신규 사용자 가입/로그인/리프레시
3. 이미지 업로드 → OCR 성공 결과 조회
4. OCR 결과 기반 Gemini 또는 OpenAI 분석 성공
5. 사용량이 Admin에서 확인 가능
6. Dashboard에 일별 지표 표시
7. Admin이 아닌 사용자는 Admin API 403
8. Swagger로 핵심 API 호출 가능

---

## 21. Risks & Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| OCR CPU 지연 | UX 저하 | 비동기 Job, 진행률 API, 페이지 제한 |
| LLM 비용 폭주 | 운영 손실 | Rate limit, quota, usage alerts |
| Provider outage | 기능 중단 | Dual provider + fallback (P1) |
| JWT 유출 | 계정 탈취 | 짧은 Access TTL, Refresh 회전, HTTPS |
| 대용량 파일 | 디스크/메모리 | size limit, streaming, object storage |
| 계층 붕괴 | 유지보수 실패 | 리뷰 게이트, 아키텍처 테스트 |
| 스펙 없는 구현 | 재작업 | Documentation Policy 강제 |

---

## 22. Open Questions

엔지니어링 Spec 착수 전 결정 필요:

1. Refresh Token 전달: **HttpOnly Cookie vs Authorization body** (보안 UX 트레이드오프)
2. 파일 스토리지: **로컬 볼륨만 v1** vs 즉시 S3 호환
3. Soft multi-tenant(`org_id`)를 v1에 포함할지
4. Worker 라이브러리 선택(예: RQ / Celery / ARQ) — Redis 전제 유지
5. Frontend 토큰 저장 및 CSRF 전략(쿠키 선택 시)
6. 기본 LLM primary provider (OpenAI vs Gemini)
7. PaddleOCR 언어 팩 기본값 및 라이선스/배포 이미지 크기 한도
8. RAG를 v1.0에 최소 인터페이스만 넣을지, v1.1로 완전 이연할지

---

## 23. Compliance & Data Handling (Baseline)

- 업로드 문서·OCR 텍스트·프롬프트는 **고객 데이터**로 취급
- 보관 기간·삭제(Right to erasure) API는 P1로 명세
- 제3자 LLM 전송 시: 사용자 고지 및 관리자 설정으로 외부 전송 on/off (P1)
- 감사 로그는 관리자 행위와 인증 실패를 우선 기록

---

## 24. Stakeholder Sign-off

| Role | Name | Date | Decision |
| --- | --- | --- | --- |
| Product Owner | | | ☐ Approve ☐ Revise |
| Tech Lead | | | ☐ Approve ☐ Revise |
| Security | | | ☐ Approve ☐ Revise |
| QA Lead | | | ☐ Approve ☐ Revise |

---

## 25. Document History

| Version | Date | Author | Changes |
| --- | --- | --- | --- |
| 1.0.0 | 2026-07-18 | Architecture | Initial production-grade PRD for AI SaaS Framework |

---

## 26. Summary

본 PRD는 AI SaaS Framework의 **제품 범위, 성공 기준, 규범적 기술 스택, 계층 아키텍처, 기능/비기능 요구사항, 데이터·API·보안·배포 계약, 단계적 로드맵**을 정의한다.

구현은 본 문서를 상위 계약으로 하고, 후속 **Architecture Spec / API Spec / Data Model Spec / Security Spec**에서 세부 스키마와 시퀀스를 고정한 뒤 코드로 내린다.

**규범 스택:** FastAPI · Next.js · PostgreSQL · Redis · Docker · SQLAlchemy · Alembic · PaddleOCR · OpenAI · Gemini · JWT · MVC · Repository Pattern.
