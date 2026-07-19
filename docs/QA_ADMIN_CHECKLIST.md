# Admin UI QA Checklist (T-10.08)

PRD §20.3 items 5–7 수동 검증용. Docker Compose + seeded admin으로 확인한다.

## Preconditions

- [ ] `docker compose up --build -d` 후 `api`/`web`/`worker` healthy
- [ ] Admin 계정 존재 (`scripts/seed.sh` 또는 DB에서 role=admin)
- [ ] 브라우저: http://localhost:3000

## Access control

- [ ] 일반 user로 로그인 후 `/admin` 접근 → `/dashboard`로 리다이렉트
- [ ] 일반 user로 `GET /api/v1/admin/dashboard` → 403 `forbidden`
- [ ] Admin 로그인 후 `/admin` 접근 가능

## Users (T-10.02)

- [ ] `/admin/users` 목록에 사용자가 보인다
- [ ] 검색(q)으로 email/name 필터된다
- [ ] role/status/name 변경 후 목록에 반영된다
- [ ] 변경 후 `/admin/audit`에 `admin.user.update` 행이 생긴다

## AI usage (T-10.03)

- [ ] 사용자 AI chat/vision 실행 후 `/admin/usage`에 행이 나타난다
- [ ] provider 필터가 동작한다

## OCR history (T-10.04)

- [ ] OCR job 생성·성공 후 `/admin/ocr`에 전역 목록이 보인다
- [ ] job 클릭 시 결과 텍스트(drill-down)가 보인다

## Audit (T-10.05)

- [ ] action 필터로 `admin.user.update`만 조회 가능
- [ ] payload에 changes가 포함된다

## Dashboard KPI (T-10.06)

- [ ] `/admin` KPI 카드가 `/api/v1/admin/dashboard`와 숫자가 일치한다
- [ ] top_users / provider_breakdown 테이블이 렌더된다

## Prompts (T-10.07)

- [ ] `/admin/prompts`에서 생성 + activate 가능
- [ ] 활성화된 prompt가 사용자 `/ai` Prompt browser에 보인다

## Sign-off

| Item | Reviewer | Date | Pass |
| --- | --- | --- | --- |
| Access control | | | |
| Users / Audit | | | |
| Usage / OCR / Dashboard | | | |
| Prompts | | | |
