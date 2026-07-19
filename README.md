# AI SaaS Framework

운영형 AI SaaS Framework 골격입니다.

| 문서 | 설명 |
| --- | --- |
| [usage.md](usage.md) | **사용법 / 테스트** (구현과 함께 갱신) |
| [usage.md §4](usage.md#4-frontend--웹-활용-가이드) | **웹(Frontend) 활용** — 화면·흐름·API-only 기능 |
| [docs/PRD.md](docs/PRD.md) | 제품 요구사항 |
| [docs/SDS.md](docs/SDS.md) | 소프트웨어 설계 |
| [docs/TASKS.md](docs/TASKS.md) | 구현 태스크 |
| [.github/copilot-instructions.md](.github/copilot-instructions.md) | 코딩 규칙 |

## Stack

FastAPI · Next.js · PostgreSQL · Redis · Docker · SQLAlchemy · Alembic · JWT  
PaddleOCR · OpenAI · Gemini · **Ollama** · Pipeline

## Architecture

```
Controller (routers) → Service → Repository → PostgreSQL
                     ↘ Adapters (OCR/LLM/Storage)   Redis (cache/queue)
Next.js (web) ──REST/JWT──► FastAPI (api)
```

- Controller에 비즈니스 로직 금지
- Spec → Implementation → Test → Docs (`usage.md` 포함)

## Status

**Phase 0~17** — v1.0.0 released; **Phase 13–17** (Ollama / S3 / RAG / soft-tenant / erasure) complete  
릴리즈: `CHANGELOG.md` · 게이트: `docs/RELEASE_GATE.md` · 다음 후보: dual-provider failover (`docs/BACKLOG_POST_V1.md`)

## Quick start

```powershell
cd <repo-root>
Copy-Item .env.example .env
docker compose up --build
```

| URL | 설명 |
| --- | --- |
| http://localhost:3000 | Frontend — 활용 가이드는 [usage.md §4](usage.md#4-frontend--웹-활용-가이드) |
| http://localhost:8000 | API (`/`, `/health`, `/ready`, `/docs`) |
| `localhost:5433` | Postgres (host) |
| `localhost:6379` | Redis |
| Compose `worker` | ARQ (OCR / pipeline / erasure 큐 소비) |

코드 변경 후 API/worker 재빌드:

```powershell
docker compose up --build --force-recreate -d api worker
```

## Layout

```
backend/     FastAPI (layered MVC + Repository)
frontend/    Next.js App Router shell
docker/      Dockerfiles & entrypoints
scripts/     migrate / seed / smoke
docs/        PRD, SDS, TASKS
usage.md     운영·개발 사용법
```

## Scripts

| Script | Purpose |
| --- | --- |
| `scripts/dev-up.sh` | `docker compose up --build` |
| `scripts/migrate.sh` | Alembic upgrade + current |
| `scripts/smoke.sh` / `smoke.ps1` | health → register/login (+ optional upload) |
| `scripts/staging-up.ps1` | Staging stack + migrate + seed |
| `scripts/seed.sh` | Admin seed + prompt seeds (T-1.07 / T-5.09) |
