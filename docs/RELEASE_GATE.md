# Release Gate Record — PRD §20.3 (T-12.03)

**Product:** AI SaaS Framework  
**Target version:** v1.0.0  
**Date:** 2026-07-19  

Evidence below is from implementation + local/staging verification paths.  
Sign the Pass column when an operator re-runs checks on the intended environment.

**Local verification run — 2026-07-19 (full Docker Compose stack):**

| # | Gate check (PRD §20.3) | Evidence / how to verify | Pass |
| --- | --- | --- | --- |
| 1 | Compose로 전체 스택 기동 | `docker compose up --build -d` → api/web/worker/postgres/redis Up; staging: `docker-compose.staging.yml` | ✅ 6개 컨테이너 Up, `/health` `/ready` ok |
| 2 | 신규 사용자 가입/로그인/리프레시 | `scripts/smoke.ps1`; FE `/register` `/login`; refresh cookie + CSRF | ✅ smoke ok + csrf/refresh 회전 확인 |
| 3 | 이미지 업로드 → OCR 성공 결과 조회 | FE Documents → OCR console; or API upload + job poll | ✅ upload 201 → OCR job `succeeded` |
| 4 | OCR 결과 기반 Gemini 또는 OpenAI 분석 성공 | FE AI vision/chat with keys set; provider via `AI_PRIMARY_PROVIDER` | ✅ chat 200 (`openai`/`gpt-4o-mini`) + OCR→vision 200 (`The text reads "HELLO OCR."`) |
| 5 | 사용량이 Admin에서 확인 가능 | `/admin/usage` + `GET /api/v1/admin/usage` | ✅ 200, page/total 응답 |
| 6 | Dashboard에 일별 지표 표시 | User `/dashboard` summary + chart; admin `/admin` KPI | ✅ `/stats/summary` 지표 반환 |
| 7 | Admin이 아닌 사용자는 Admin API 403 | Non-admin → `/admin` redirect; API 403 `forbidden` | ✅ 일반 유저 `/admin/usage` 403 |
| 8 | Swagger로 핵심 API 호출 가능 | http://localhost:8000/docs (staging `:18000/docs`) | ✅ `/docs` 200, `/openapi.json` 200 |

### 검증 중 발견·수정한 이슈 (Gate 3)

Worker 컨테이너에서 OCR이 실패하던 문제를 실행 검증으로 발견하여 수정:

1. `libGL.so.1: cannot open shared object file` — `docker/backend.Dockerfile`에 `libgl1` 등 런타임 공유 라이브러리 설치 추가.
2. `ModuleNotFoundError: No module named 'setuptools'` (paddle `cpp_extension` import 시) — `backend/requirements.txt`에 `setuptools` 명시.

수정 후 재빌드하여 업로드→OCR `succeeded` 확인.

> Gate 4는 유일한 미결 항목이었으며 **코드 결함이 아니라 자격증명 부재**였습니다.  
> 2026-07-19 재검증: `OPENAI_API_KEY` 설정 후 chat + OCR→vision 모두 200 통과.

## Supporting artifacts

- Smoke: `scripts/smoke.ps1` / `scripts/smoke.sh`
- Admin QA: [QA_ADMIN_CHECKLIST.md](QA_ADMIN_CHECKLIST.md)
- OpenAPI ≥95%: [OPENAPI_COVERAGE.md](OPENAPI_COVERAGE.md)
- Production pack: [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md)
- Deploy order: [RUNBOOK_DEPLOY.md](RUNBOOK_DEPLOY.md)

## Sign-off

| Role | Name | Date | Signature |
| --- | --- | --- | --- |
| Engineering | | | |
| QA / Operator | | | |

> Implementation status: all eight capabilities are present in codebase (Phases 0–12).  
> Local run 2026-07-19: **8/8 게이트 통과** (Gate 4는 API 키 설정 후 재확인).  
> Gate is **satisfied for release readiness** once the Pass boxes are checked on a live stack.
