# AI SaaS Framework — 사용법 (usage)

구현 진행에 맞춰 이 문서를 갱신합니다.  
현재 반영 범위: … **Phase 12 complete / v1.0.0 ready** (T-12.01 ~ T-12.05 — staging compose, deploy runbook, release gate, changelog, backlog)

관련 명세: [docs/PRD.md](docs/PRD.md) · [docs/SDS.md](docs/SDS.md) · [docs/TASKS.md](docs/TASKS.md)

---

## 1. 사전 요구사항

- Docker Desktop (Compose v2) — 최소 Postgres / Redis용
- **하이브리드 로컬** 시: Python 3.11+, Node.js 20+ (npm)
- PowerShell 또는 bash

### 포트

| 서비스 | 호스트 | 컨테이너 |
| --- | --- | --- |
| Web (Next.js) | `3000` | `3000` |
| API (FastAPI) | `8000` | `8000` |
| PostgreSQL | `5433` | `5432` |
| Redis | `6379` | `6379` |
| Worker (ARQ) | — | (내부; Redis 큐 소비) |

> 호스트에서 DB에 접속할 때는 반드시 **`localhost:5433`** 을 사용하세요.

### 기동 방식 선택

| 방식 | Postgres / Redis | API / Worker / Web | 언제 |
| --- | --- | --- | --- |
| **전체 Docker** (§3) | Compose | Compose | 한 번에 올리기, CI/스테이징에 가깝게 |
| **하이브리드** (§3.1) | Compose만 | 호스트(uvicorn / arq / next) | 일상 개발 — Docker 부하·메모리 절약 |

---

## 2. 환경변수

```powershell
cd <repo-root>
Copy-Item .env.example .env
```

- `.env`는 커밋하지 않습니다.
- 호스트 도구: `DATABASE_URL=...@localhost:5433/...`
- Compose `api`: `postgres:5432`, `redis:6379` 로 오버라이드
- Compose `web`: `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` (브라우저 → 호스트 API)

---

## 3. Docker로 전체 기동

```powershell
cd <repo-root>
docker compose up --build
```

백그라운드:

```powershell
docker compose up --build -d
docker compose ps
```

기대 컨테이너: `aisaas-postgres`, `aisaas-redis`, `aisaas-api`, `aisaas-web`

### 개별 재빌드

```powershell
# API (코드 변경 후 필수)
docker compose up --build --force-recreate -d api

# Frontend shell
docker compose up --build --force-recreate -d web
```

중지:

```powershell
docker compose down
```

### API entrypoint wait-for-deps (T-0.08)

`api`는 Postgres/Redis TCP가 열릴 때까지 대기 후 uvicorn 기동.

| 환경변수 | 기본 | 의미 |
| --- | --- | --- |
| `WAIT_FOR_DEPS` | `1` | `0`이면 대기 생략 |
| `WAIT_FOR_DEPS_MAX_ATTEMPTS` | `60` | 최대 시도 |
| `WAIT_FOR_DEPS_SLEEP_SECONDS` | `2` | 간격(초) |

---

## 3.1 하이브리드 로컬 기동 (Postgres/Redis만 Docker)

API·Worker·Frontend는 **호스트**에서 돌리고, DB/캐시만 Docker로 올리는 방식입니다.  
C 드라이브/WSL 메모리가 빠듯할 때(전체 Compose보다) 안정적으로 개발하기 좋습니다.

### 3.1.1 인프라만 올리기

전체 `api` / `web` / `worker`를 띄우지 않습니다. 이미 떠 있으면 중지하세요.

```powershell
cd <repo-root>

# (선택) 풀 스택이 떠 있으면 API/Web/Worker만 내리기 — DB 데이터는 유지
docker compose stop api web worker

# Postgres + Redis만
docker compose up -d postgres redis
docker compose ps
```

기대: `aisaas-postgres` · `aisaas-redis` 가 `healthy`.

### 3.1.2 환경변수 (호스트용)

```powershell
cd <repo-root>
Copy-Item .env.example .env   # 없을 때만
```

호스트에서 돌릴 때 `.env`에서 특히 확인할 값:

| 변수 | 호스트용 예시 | 설명 |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+asyncpg://aisaas:aisaas@localhost:5433/ai_saas` | Compose 게시 포트 **5433** |
| `REDIS_URL` | `redis://localhost:6379/0` | |
| `CORS_ORIGINS` | `http://localhost:3000` | FE origin |
| `STORAGE_PATH` | `.\data\storage` (또는 절대 경로) | Linux 경로 `/data/storage` 는 Windows 호스트에서 쓰지 말 것 |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | FE → API (브라우저 기준) |
| `SEED_ADMIN_*` | `.env.example` 참고 | seed 시 관리자 계정 |

Windows에서 저장 디렉터리 예:

```powershell
# repo-root 기준
New-Item -ItemType Directory -Force -Path .\data\storage | Out-Null
# .env 에 STORAGE_PATH=./data/storage 또는 절대 경로 설정
```

### 3.1.3 Backend (API)

터미널 1:

```powershell
cd <repo-root>\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

# 마이그레이션 (최초 1회 및 스키마 변경 시)
python -m alembic upgrade head

# (선택) 관리자 + 프롬프트 시드
python -m app.scripts.seed_admin
python -m app.scripts.seed_prompts

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

확인:

- http://localhost:8000/health → `{"status":"ok"}`
- http://localhost:8000/ready → postgres/redis ok
- http://localhost:8000/docs

> OCR(PaddleOCR)까지 호스트에서 쓰려면 `requirements.txt`의 paddle 계열이 설치되어야 하며, 용량·빌드 시간이 큽니다. API만 먼저 올릴 때는 CI용 `requirements-ci.txt`로도 대부분 기능 검증이 가능하지만 OCR 실행은 불가합니다.

### 3.1.4 Worker (ARQ) — OCR/파이프라인/통계용

백그라운드 잡이 필요하면 **별도 터미널**에서 API와 같은 venv로:

```powershell
cd <repo-root>\backend
.\.venv\Scripts\Activate.ps1
arq app.workers.settings.WorkerSettings
```

Worker 없이 API만 띄워도 로그인·문서·Admin·채팅 등은 동작합니다. OCR 잡/파이프라인 enqueue는 Worker가 소비해야 완료됩니다.

### 3.1.5 Frontend (Next.js)

터미널 3:

```powershell
cd <repo-root>\frontend
npm install
npm run dev
# http://localhost:3000
```

로그인(시드 후): `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` (예: `admin@example.com` / `ChangeMeAdmin1!`)

### 3.1.6 한눈에 보는 터미널 구성

| 터미널 | 명령 | URL |
| --- | --- | --- |
| A | `docker compose up -d postgres redis` | DB `5433`, Redis `6379` |
| B | `uvicorn app.main:app --reload --port 8000` (`backend/`) | http://localhost:8000 |
| C | `arq app.workers.settings.WorkerSettings` (`backend/`) | (큐 소비) |
| D | `npm run dev` (`frontend/`) | http://localhost:3000 |

### 3.1.7 하이브리드 중지

```powershell
# 호스트: Ctrl+C 로 uvicorn / arq / next 종료

# 인프라만 유지하려면 Postgres/Redis는 그대로 두고
# 전부 내리려면:
docker compose stop postgres redis
# 또는
docker compose down
```

> `docker compose down -v` 는 **볼륨(DB 데이터) 삭제**이므로 로컬 데이터가 날아갑니다.

### 3.1.8 포트 충돌 주의

하이브리드로 호스트 API(`8000`) / FE(`3000`)를 쓰는 동안 Compose의 `api`/`web`도 올리면 포트가 겹칩니다.  
§3.1.1처럼 `docker compose stop api web worker` 후 호스트 프로세스를 기동하세요.

---

## 4. Frontend

- URL: http://localhost:3000
- Next.js App Router — 로그인·Documents·OCR·AI·Pipelines·Dashboard·Admin UI 포함 (Phase 8~10)
- API는 `NEXT_PUBLIC_API_BASE_URL`(기본 `http://localhost:8000`)로 호출

로컬(호스트) FE만 실행할 때는 §3.1.5와 동일합니다.

```powershell
cd frontend
npm install
npm run dev
# http://localhost:3000
```

Compose로 FE까지 올릴 때는 §3 `docker compose up` 의 `web` 서비스를 사용합니다.

---

## 5. API 엔드포인트

Base: `http://localhost:8000`

| Method | Path | 설명 | 성공 |
| --- | --- | --- | --- |
| GET | `/` | 루트 프로브 | message + app_env |
| GET | `/health` | Liveness | `{ "status": "ok" }` |
| GET | `/ready` | Postgres+Redis | status/postgres/redis |
| GET | `/docs` | Swagger | — |
| POST | `/api/v1/auth/register` | 회원가입 | 201 `{ user }` |
| POST | `/api/v1/auth/login` | 로그인 | 200 token + `refresh_token`/`csrf_token` 쿠키 |
| POST | `/api/v1/auth/refresh` | 토큰 회전 | 200 + `X-CSRF-Token` 헤더 필수 |
| POST | `/api/v1/auth/logout` | 로그아웃 | 204 |
| GET | `/api/v1/auth/csrf` | CSRF 발급 | `{ csrf_token }` + 쿠키 |
| GET | `/api/v1/_probe/me` | (T-1.05 stub) Bearer 필요 | 200 UserRead / 401 |
| GET | `/api/v1/_probe/admin` | (T-1.05 stub) admin role | 200 / 401 / 403 |
| GET | `/api/v1/users/me` | 내 프로필 (Bearer) | UserRead |
| PATCH | `/api/v1/users/me` | 이름 수정 (`name`만) | UserRead |
| GET | `/api/v1/admin/users` | 사용자 목록 (admin) | Page |
| GET | `/api/v1/admin/users/{id}` | 사용자 상세 (admin) | UserRead |
| PATCH | `/api/v1/admin/users/{id}` | role/status/name + audit | UserRead |
| POST | `/api/v1/documents` | 파일 업로드 (multipart) | 201 DocumentRead |
| GET | `/api/v1/documents` | 내 문서 목록 | Page |
| GET | `/api/v1/documents/{id}` | 문서 메타 (owner/admin) | DocumentRead |
| DELETE | `/api/v1/documents/{id}` | soft delete | 204 |

### Auth 수동 테스트 (Swagger)

1. http://localhost:8000/docs 열기
2. `POST /api/v1/auth/register` → email/password/name
3. `POST /api/v1/auth/login` → 동일 자격증명 (브라우저가 쿠키 저장)
4. `GET /api/v1/auth/csrf` 또는 login 응답 쿠키의 `csrf_token`을 `X-CSRF-Token`에 넣어 `POST /api/v1/auth/refresh`
5. `POST /api/v1/auth/logout` (동일 CSRF 헤더)

API 재빌드 후 쿠키 경로가 보이려면:

```powershell
docker compose up --build --force-recreate -d api
```

### PowerShell

```powershell
(Invoke-RestMethod http://localhost:8000/) | ConvertTo-Json
(Invoke-RestMethod http://localhost:8000/health) | ConvertTo-Json
(Invoke-RestMethod http://localhost:8000/ready) | ConvertTo-Json
```

Request ID:

```powershell
$r = Invoke-WebRequest http://localhost:8000/health -Headers @{ "X-Request-ID" = "manual-001" }
$r.Headers["X-Request-ID"]
```

Ready 실패 테스트:

```powershell
docker compose stop redis
# /health → 200, /ready → 503
docker compose start redis
```

---

## 6. Alembic

```powershell
cd backend
python -m pip install -r requirements.txt
python -m alembic current
python -m alembic upgrade head
```

현재 head: `0006_ocr` (`ocr_jobs`, `ocr_results` + ENUM `ocr_job_status`)

다운그레이드 검증:

```powershell
cd backend
python -m alembic downgrade 0005_documents
python -m alembic upgrade head
```

```powershell
bash scripts/migrate.sh
```

---

## 6.1 Security unit tests (T-1.02)

```powershell
cd backend
python -m pip install -r requirements.txt
python -m pytest app/tests/unit/test_security.py -v
```

검증 범위: Argon2id hash/verify, JWT claim round-trip, 만료·변조 거부, refresh token SHA-256.

### AuthService tests (T-1.03)

Postgres + Redis가 떠 있어야 합니다 (`docker compose up -d postgres redis`).

```powershell
cd backend
python -m pytest app/tests/unit/test_auth_service.py -v
```

검증 범위: register/login 성공, 중복 email, 잘못된 비밀번호, inactive, refresh 회전·reuse 감지, logout, login rate limit.

### Auth HTTP routes (T-1.04)

```powershell
cd backend
python -m pytest app/tests/api/test_auth_routes.py -v
```

### Auth Depends (T-1.05)

```powershell
cd backend
python -m pytest app/tests/api/test_auth_deps.py -v
```

Swagger에서 Authorize에 Bearer access token을 넣은 뒤 `GET /api/v1/_probe/me` · `/_probe/admin` 호출.

### Auth API suite (T-1.06, CI)

Postgres + Redis 기동 후:

```powershell
cd backend
python -m pytest -m auth -v
# 또는 전체
python -m pytest
```

포함: rate limit(429), inactive login(403), CSRF 실패(403), reuse, error envelope, Depends 401/403.

### Users / Admin RBAC (T-2.06)

```powershell
cd backend
python -m pytest -m rbac -v
```

### Admin seed (T-1.07)

`.env`에 `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` / `SEED_ADMIN_NAME` 설정 후:

```powershell
# Git Bash / WSL
bash scripts/seed.sh

# 또는
cd backend
python -m app.scripts.seed_admin
```

- 이메일이 없으면 `role=admin` 사용자 생성
- 이미 있으면 skip (idempotent; role/status만 admin/active로 보정)
- 로그인 후 `GET /api/v1/_probe/admin` 으로 확인

---

## 7. 스크립트

| 스크립트 | 용도 |
| --- | --- |
| `scripts/dev-up.sh` | `docker compose up --build` |
| `scripts/migrate.sh` | Alembic upgrade + current |
| `scripts/smoke.sh` | `/health` + `/ready` |
| `scripts/seed.sh` | Admin seed (`SEED_ADMIN_*`) |

```powershell
# Git Bash / WSL
bash scripts/smoke.sh

# 또는
$env:API_BASE="http://localhost:8000"; bash scripts/smoke.sh
```

---

## 8. 구현 상태 요약

| Task | 내용 | 상태 |
| --- | --- | --- |
| T-0.01 | 프로젝트 레이아웃 | Done |
| T-0.02 | `.env.example` | Done |
| T-0.03 | Compose postgres/redis | Done |
| T-0.04 | FastAPI + Docker api | Done |
| T-0.05 | Settings / log / Request-ID / errors | Done |
| T-0.06 | SQLAlchemy + Alembic baseline | Done |
| T-0.07 | Redis + `/health` `/ready` | Done |
| T-0.08 | Entrypoint wait-for-deps | Done |
| T-0.09 | Frontend Docker `web` shell | Done |
| T-0.10 | README | Done |
| T-0.11 | smoke/migrate 스크립트 | Done |
| T-1.01 | users / refresh_tokens 마이그레이션 | Done |
| T-1.02 | Argon2id + JWT issue/verify | Done |
| T-1.03 | Auth repositories + AuthService | Done |
| T-1.04 | Auth routers + schemas | Done |
| T-1.05 | current_user / role guard | Done |
| T-1.06 | Auth API test suite | Done |
| T-1.07 | Admin seed | Done |
| T-2.01 | permissions / role_permissions + seed | Done |
| T-2.02 | GET/PATCH `/users/me` | Done |
| T-2.04 | AuditLog + AuditService.write | Done |
| T-2.03 | Admin users API + audit hook | Done |
| T-2.06 | Users/Admin RBAC tests | Done |
| T-3.01 | documents 테이블 마이그레이션 | Done |
| T-3.02 | StoragePort + LocalStorage + Compose volume | Done |
| T-3.03 | DocumentService + `/documents` API | Done |
| T-3.04 | Document API tests (413/415/404/ownership) | Done |
| T-4.01 | ocr_jobs / ocr_results 마이그레이션 | Done |
| T-4.02 | ARQ worker + QueuePublisher + Compose `worker` | Done |
| T-4.03 | ImagePreprocessPort + OpenCV (deskew/denoise/contrast) | Done |
| T-4.04 | OcrEnginePort + PaddleOCR (`korean+en`) | Done |
| T-4.05 | OCR jobs API + worker (`queued→succeeded`) | Done |
| T-4.06 | OCR retry/backoff + failure persistence | Done |
| T-4.07 | OCR page limit / PDF page split | Done |
| T-4.08 | OCR API + worker integration tests | Done |
| T-4.09 | Queued-job reconciler (Redis loss recovery) | Done |
| T-5.01 | ai_prompts / ai_requests / ai_usages 마이그레이션 | Done |
| T-5.02 | LlmProviderPort + OpenAI adapter | Done |
| T-5.03 | Gemini adapter (same LlmProviderPort) | Done |
| T-5.04 | LLM factory (primary/fallback) | Done |
| T-5.05 | PromptService + `/ai/prompts*` | Done |
| T-5.06 | AiService chat/vision + usage | Done |
| T-5.07 | AI per-user rate limit (Redis 429) | Done |
| T-5.08 | Streaming chat SSE (`/ai/chat/stream`) | Done |
| T-5.09 | Prompt seed pack (idempotent) | Done |
| T-5.10 | Ollama adapter stub (v1.1) | Done |
| T-5.11 | AI API tests | Done |
| T-6.01 | Alembic `pipeline_runs` | Done |
| T-6.02 | PipelineService + worker + `/pipelines/*` | Done |
| T-6.03 | Partial-stage failure reporting | Done |
| T-6.04 | Pipeline API/worker tests | Done |
| T-7.01 | Alembic `stat_daily` | Done |
| T-7.02 | Stats materialize worker (10분 cron) | Done |
| T-7.03 | Stats routers (daily/monthly/summary + scope) | Done |
| T-7.04 | Stats CSV export | Done |
| T-7.05 | Redis summary cache (5m) | Done |
| T-7.06 | Stats API tests | Done |
| T-8.01 | Route groups + AppShell layouts | Done |
| T-8.02 | HTTP client + refresh/CSRF | Done |
| T-8.03 | Login / register / logout UI | Done |
| T-8.04 | Auth + admin route guards | Done |
| T-8.05 | UI primitives (Button/Input/Table/Modal) | Done |
| T-8.06 | `NEXT_PUBLIC_API_BASE_URL` docs | Done |
| T-8.07 | ESLint + Prettier | Done |
| T-9.01 | Documents UI | Done |
| T-9.02 | OCR console + polling | Done |
| T-9.03 | AI chat/vision UI | Done |
| T-9.04 | Pipelines UI + polling | Done |
| T-9.05 | User dashboard summary | Done |
| T-9.06 | Daily stats charts (recharts) | Done |
| T-9.07 | Prompt browser (read-only) | Done |
| T-9.08 | Empty/error/loading polish | Done |
| T-10.01 | Admin API usage/ocr/audit/dashboard | Done |
| T-10.02 | Admin users UI | Done |
| T-10.03 | Admin AI usage UI | Done |
| T-10.04 | Admin OCR history UI | Done |
| T-10.05 | Admin audit log UI | Done |
| T-10.06 | Admin dashboard KPI UI | Done |
| T-10.07 | Admin prompt management UI | Done |
| T-10.08 | Admin QA checklist | Done |
| T-11.01 | GitHub Actions CI | Done |
| T-11.02 | Compose smoke (register/login) | Done |
| T-11.03 | OpenAPI coverage ≥95% | Done |
| T-11.04 | PR template layer checklist | Done |
| T-11.05 | Security hardening notes | Done |
| T-11.06 | Rate-limit ops defaults | Done |
| T-11.07 | Backup/restore runbook | Done |
| T-11.08 | Perf baseline notes | Done |
| T-11.09 | Data retention spike (P1) | Done |
| T-12.01 | Staging Compose + `.env.staging.example` | Done |
| T-12.02 | Deploy runbook (migrate→api→worker→web) | Done |
| T-12.03 | Release gate PRD §20.3 record | Done |
| T-12.04 | CHANGELOG v1.0.0 (+ tag instructions) | Done |
| T-12.05 | Post-v1 backlog | Done |
| **다음** | Operator sign-off + optional `git tag v1.0.0` | — |

### Deployment / Release (T-12)

| Artifact | Path |
| --- | --- |
| Staging Compose | `docker-compose.staging.yml` |
| Staging env sample | `.env.staging.example` |
| Staging helper | `scripts/staging-up.ps1` |
| Deploy runbook | `docs/RUNBOOK_DEPLOY.md` |
| Release gate | `docs/RELEASE_GATE.md` |
| Changelog | `CHANGELOG.md` |
| Post-v1 backlog | `docs/BACKLOG_POST_V1.md` |

```powershell
Copy-Item .env.staging.example .env.staging
# edit secrets, then:
powershell -File scripts/staging-up.ps1 -Build
$env:API_BASE="http://localhost:18000"; powershell -File scripts/smoke.ps1
```

### Quality / CI / Hardening (T-11)

| Artifact | Path |
| --- | --- |
| CI workflow | `.github/workflows/ci.yml` |
| Smoke | `scripts/smoke.sh` (`SMOKE_UPLOAD=1` optional) |
| OpenAPI review | `docs/OPENAPI_COVERAGE.md` |
| Security | `docs/SECURITY_HARDENING.md` |
| Rate limits | `docs/OPS_DEFAULTS.md` |
| Backup | `docs/RUNBOOK_BACKUP.md` |
| Perf | `docs/PERF_BASELINE.md` |
| Erasure spike | `docs/SPIKE_DATA_RETENTION.md` |
| Prod checklist | `docs/PRODUCTION_CHECKLIST.md` |

```powershell
# Smoke (API must be up)
powershell -File scripts/smoke.ps1
powershell -File scripts/smoke.ps1 -Upload
# or (Git Bash / Linux): bash scripts/smoke.sh

# Local CI-like backend tests (skip real Paddle)
cd backend
python -m pytest --ignore=app/tests/unit/test_paddle_ocr.py -k "not real_fixture_opencv_paddle" --tb=short
```
### Admin (T-10.01 ~ T-10.08)

| Method | Path | Auth | 설명 |
| --- | --- | --- | --- |
| GET | `/api/v1/admin/usage` | Admin | AI usage 목록 (from/to/provider/user_id) |
| GET | `/api/v1/admin/ocr-history` | Admin | 전역 OCR jobs |
| GET | `/api/v1/admin/ocr-history/{id}` | Admin | job + result pages |
| GET | `/api/v1/admin/audit-logs` | Admin | 감사 로그 |
| GET | `/api/v1/admin/dashboard` | Admin | 24h KPI + top_users + provider_breakdown |

FE routes: `/admin`, `/admin/users`, `/admin/usage`, `/admin/ocr`, `/admin/audit`, `/admin/prompts`  
수동 QA: [docs/QA_ADMIN_CHECKLIST.md](docs/QA_ADMIN_CHECKLIST.md)

```powershell
cd backend
python -m pytest app/tests/api/test_admin_ops.py app/tests/api/test_admin_users.py -v
cd ../frontend
npm run build
```

### Frontend (T-8.01 ~ T-9.08)

| Route | Auth | 설명 |
| --- | --- | --- |
| `/login`, `/register` | Public | JWT login + HttpOnly refresh cookie |
| `/dashboard` | User | Summary cards + 14d chart + recent OCR |
| `/documents` | User | Upload / list / delete |
| `/ocr` | User | Create job + poll + results |
| `/ai` | User | Chat / vision / active prompts |
| `/pipelines` | User | Create run + stage polling |
| `/admin/*` | Admin | Shell only (feature UI → Phase 10) |

```powershell
cd frontend
npm install
npm run lint
npm run build
npm run dev   # http://localhost:3000 — API must be up at NEXT_PUBLIC_API_BASE_URL
```

Access token은 메모리만 사용(ADR-029). 401 시 `/auth/refresh` 1회 재시도(+ CSRF).
Admin 비사용자는 `/admin` 접근 시 `/dashboard`로 리다이렉트.

### Statistics (T-7.01 ~ T-7.06)

| Method | Path | Auth | 설명 |
| --- | --- | --- | --- |
| GET | `/api/v1/stats/daily?from&to&metric&scope` | User | 일별 포인트 (`scope=global`은 admin) |
| GET | `/api/v1/stats/monthly?from_month&to_month&metric&scope` | User | 월별 rollup (`*.avg`는 평균, 나머지 합계) |
| GET | `/api/v1/stats/summary` | User | 오늘 KPI (live + Redis 5m 캐시) |
| GET | `/api/v1/stats/export?from&to&format=csv` | User | CSV 다운로드 |

Metrics (SDS §9.8): `ocr.jobs.count` `ocr.jobs.failed` `ocr.jobs.latency_ms.avg`
`ai.requests.count` `ai.tokens.in` `ai.tokens.out` `ai.cost.estimate`
`pipeline.runs.count` `auth.login.failed`(global/admin 전용, 로그인 실패 audit에서 집계)

Materialize: ARQ cron `materialize_daily_stats` (10분마다, 오늘+어제 delete+insert; idempotent).
수동 백필: worker 컨텍스트에서 `enqueue('materialize_daily_stats', '2026-07-18')`.

Env: `STATS_MATERIALIZE_ENABLED`(기본 true) / `STATS_SUMMARY_CACHE_SECONDS`(기본 300).
캐시 키: `aisaas:cache:stats:{user_id}:{day}`.

```powershell
cd backend
python -m alembic upgrade head
python -m pytest app/tests/integration/test_stats_schema.py app/tests/api/test_stats.py -v
```

### Pipelines (T-6.01 ~ T-6.04)

| Method | Path | Auth | 설명 |
| --- | --- | --- | --- |
| POST | `/api/v1/pipelines/runs` | User | 시작 → `202` queued + ARQ `run_pipeline` |
| GET | `/api/v1/pipelines/runs` | User | 목록 |
| GET | `/api/v1/pipelines/runs/{id}` | User | 상태·스테이지 폴링 |

Stages: `preprocess` → `ocr` → `ai_analyze` → `persist`  
실패 시 이전 스테이지 `succeeded` + `output_ref` 유지, 이후는 `pending` (T-6.03).

기본 AI 프롬프트: `ocr.analyze.summary` (시드 권장: `python -m app.scripts.seed_prompts`).

```powershell
cd backend
python -m alembic upgrade head
python -m pytest app/tests/integration/test_pipeline_schema.py app/tests/api/test_pipelines.py -v
```

### AI APIs (T-5.05 ~ T-5.11)

| Method | Path | Auth | 설명 |
| --- | --- | --- | --- |
| GET | `/api/v1/ai/prompts` | User | 목록 (`name`, `active` 필터) |
| GET | `/api/v1/ai/prompts/{id}` | User | 상세 |
| POST | `/api/v1/ai/prompts` | Admin | 생성 (`activate?`) |
| PATCH | `/api/v1/ai/prompts/{id}` | Admin | 수정 / `create_new_version` |
| POST | `/api/v1/ai/prompts/{id}/activate` | Admin | name당 1 active |
| POST | `/api/v1/ai/chat` | User | Chat + `ai_requests`/`ai_usages` |
| POST | `/api/v1/ai/chat/stream` | User | SSE (`meta` → `delta`* → `done`) |
| POST | `/api/v1/ai/vision` | User | Vision (`document_id` / `ocr_job_id` / `image_document_id`) |

Rate limit (T-5.07): Redis `aisaas:rl:ai:{user_id}`, env `AI_RATE_LIMIT_MAX` (default 60) / `AI_RATE_LIMIT_WINDOW_SECONDS` (60).

SSE 클라이언트 예:

```powershell
# Bearer 필요. 이벤트: meta, delta, done
curl.exe -N -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" `
  -d '{\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}]}' `
  http://localhost:8000/api/v1/ai/chat/stream
```

Prompt seed (T-5.09):

```powershell
cd backend
python -m app.scripts.seed_prompts
# 또는 scripts/seed.sh (admin + prompts)
```

Ollama (T-5.10): `OllamaAdapter` 스텁만 존재 — **v1.1**, `LlmFactory`에 미등록.

```powershell
cd backend
python -m pytest app/tests/api/test_ai.py app/tests/unit/test_ollama_adapter.py -v
```

### LLM factory (T-5.04)

Env만으로 primary 전환 (코드 변경 없음):

| Env | 기본 | 설명 |
| --- | --- | --- |
| `AI_PRIMARY_PROVIDER` | `openai` | `openai` \| `gemini` |
| `AI_FALLBACK_PROVIDER` | `gemini` | fallback 대상 |
| `AI_FALLBACK_ENABLED` | `false` | `true`면 primary `ProviderError` 시 fallback 1회 |

- `LlmFactory.resolve()` / `get_llm_factory()`
- 요청에서 provider를 명시하면 fallback 래핑 없음

```powershell
cd backend
python -m pytest app/tests/unit/test_llm_factory.py -v
```

### Gemini adapter (T-5.03)

- Adapter: `GeminiAdapter` (`google-genai`); default model `gemini-2.0-flash`
- Port parity: `chat` / `vision` / `health` + same error mapping (429/502/422)

```powershell
cd backend
python -m pytest app/tests/unit/test_gemini_adapter.py -v
```

### OpenAI adapter (T-5.02)

- Port: `LlmProviderPort` — `chat` / `vision` / `health`
- Adapter: `OpenAiAdapter` (`openai` SDK); default model `gpt-4o-mini`
- Errors: rate limit → 429, timeout/upstream → 502 (`ProviderError`), bad request → 422

```powershell
cd backend
python -m pytest app/tests/unit/test_openai_adapter.py -v
```

### AI schema (T-5.01)

- Migration: `0007_ai` (head)
- Tables: `ai_prompts` (unique name+version, partial unique active name), `ai_requests`, `ai_usages` (1:1 request)
- ENUMs: `ai_provider`, `ai_request_type`, `ai_request_status`

```powershell
cd backend
alembic upgrade head
python -m pytest app/tests/integration/test_ai_schema.py -v
```

### OCR reconciler ops (T-4.09)

Redis 큐가 유실돼도 Postgres `ocr_jobs`가 SoR입니다. worker ARQ cron(매분 `:00`)이:

| 상태 | 조건 | 동작 |
| --- | --- | --- |
| `queued` | `updated_at` > `OCR_STALE_QUEUED_SECONDS` (default 180) | `run_ocr_job` 재enqueue |
| `running` | `started_at` > `OCR_STALE_RUNNING_SECONDS` (default 1200) | `queued`로 리셋(attempt 유지) 후 재enqueue |

- 비활성: `OCR_RECONCILE_ENABLED=false`
- 코드: `OcrReconcileService` + `reconcile_stale_ocr_jobs`

```powershell
cd backend
python -m pytest app/tests/unit/test_ocr_reconcile.py -v
```

### OCR integration tests (T-4.08)

- Marker: `integration`
- Mocked engine path + real fixture (`sample_ocr_text.png` → OpenCV + PaddleOCR)

```powershell
cd backend
python -m pytest app/tests/integration/test_ocr_pipeline.py -v -m integration
```

전체 OCR 관련:

```powershell
python -m pytest app/tests/api/test_ocr.py app/tests/api/test_ocr_pages.py app/tests/integration/test_ocr_pipeline.py app/tests/unit/test_ocr_retry.py app/tests/unit/test_paddle_ocr.py -v
```

### OCR page limit / PDF (T-4.07)

- Upload 시 PDF `page_count` 자동 기록 (이미지=1)
- `POST /ocr/jobs`: `page_count > OCR_MAX_PAGES` → **422**
- Worker: PDF → 페이지별 PNG 렌더 → 페이지별 `ocr_results`
- Worker에서도 한도 초과 시 **재시도 없이** `failed` + clear error

```powershell
cd backend
python -m pytest app/tests/api/test_ocr_pages.py -v
```

### OCR retry (T-4.06)

- Env: `OCR_MAX_ATTEMPTS` (default 3), `OCR_RETRY_BASE_SECONDS` (default 2 → 2s, 4s, 8s…)
- 실패 시: `attempt_count` 증가 → 한도 내이면 `queued` + ARQ `_defer_by` 재enqueue
- 한도 소진: `status=failed`, `error` 저장, `finished_at` 설정
- Job GET 응답에 `attempt_count` 포함

```powershell
cd backend
python -m pytest app/tests/api/test_ocr.py app/tests/unit/test_ocr_retry.py -v
```

### OCR jobs API (T-4.05)

| Method | Path | 설명 |
| --- | --- | --- |
| POST | `/api/v1/ocr/jobs` | job 생성 → `202` + ARQ enqueue |
| GET | `/api/v1/ocr/jobs` | 내 job 목록 |
| GET | `/api/v1/ocr/jobs/{id}` | 상태 폴링 |
| GET | `/api/v1/ocr/jobs/{id}/results` | 결과 (`succeeded`만, 아니면 409) |

Worker: `run_ocr_job` — Storage → OpenCV preprocess → PaddleOCR → `ocr_results`.

```powershell
cd backend
python -m pytest app/tests/api/test_ocr.py -v
```

(테스트는 Fake OCR로 lifecycle 검증; 실제 Paddle은 unit `test_paddle_ocr.py`)

### PaddleOCR (T-4.04)

- Port: `OcrPageResult` + `OcrEnginePort`
- Adapter: `PaddleOcrAdapter` — product lang `korean+en` → Paddle `korean`
- Stack pin: `paddlepaddle` 2.6.x + `paddleocr` 2.7.x + `numpy` 1.x (Windows ABI)
- Fixture: `app/tests/fixtures/sample_ocr_text.png` (`HELLO OCR`)

```powershell
cd backend
python -m pytest app/tests/unit/test_paddle_ocr.py -v
```

첫 실행 시 모델이 `~/.paddleocr` 로 다운로드됩니다.

### OpenCV preprocess (T-4.03)

- Port: `PreprocessOptions` + `ImagePreprocessPort` (`app/adapters/ports.py`)
- Adapter: `OpenCvPreprocessAdapter` → PNG bytes
- Fixture: `app/tests/fixtures/sample_preprocess.png`

```powershell
cd backend
python -m pytest app/tests/unit/test_opencv_preprocess.py -v
```

### ARQ Worker (T-4.02)

Compose에 `worker` 서비스가 추가됩니다 (API와 동일 이미지, 커맨드만 다름):

```text
arq app.workers.settings.WorkerSettings
```

- Publisher: `app/adapters/queue_publisher.py` (`enqueue` / `enqueue_noop`)
- Smoke job: `noop_job` — enqueue → worker → result 왕복 검증

```powershell
cd backend
python -m pytest app/tests/unit/test_queue_worker.py -v
```

Worker만 재기동:

```powershell
docker compose up --build --force-recreate -d worker
```

### Documents API tests (T-3.04)

```powershell
cd backend
python -m pytest app/tests/api/test_documents.py -v
```

커버: happy path, 415 MIME, 413 size, 404, ownership 403, admin 조회, empty 422.

### Storage (T-3.02)

- Compose `api` 마운트: named volume `aisaas_storage` → `/data/storage` (`STORAGE_PATH`)
- 키 형식: `documents/YYYY/MM/{document_uuid}/original.bin`
- 단위 테스트: `python -m pytest app/tests/unit/test_local_storage.py -v`

---

## 9. 문제 해결

| 증상 | 조치 |
| --- | --- |
| `/health` 404 | Compose API: `docker compose up --build --force-recreate -d api` / 호스트: uvicorn 기동 여부 확인 |
| Alembic @ 5432 실패 | `.env`를 `localhost:5433`으로 |
| `/ready` 503 | `docker compose ps` — postgres/redis healthy 확인 |
| `web` 안 뜸 | Compose: `docker compose logs web` / 호스트: `npm run dev` 로그 |
| 포트 3000/8000 충돌 | Compose `api`/`web`와 호스트 프로세스 동시 기동 금지 → `docker compose stop api web` |
| 하이브리드에서 업로드/OCR 경로 오류 | `.env`의 `STORAGE_PATH`를 Windows 경로(`./data/storage` 등)로 |
| Docker `Internal Server Error for API route` | Docker Desktop/WSL 재시작; `.wslconfig` memory/swap·호스트 RAM 여유 확인 |

---

## 10. 문서 갱신 규칙

새 태스크 구현 시 이 파일에 기동 변경 · API/CLI · 테스트 · 상태 표를 추가합니다.
