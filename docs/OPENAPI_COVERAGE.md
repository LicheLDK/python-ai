# OpenAPI Coverage vs SDS §9 (T-11.03)

Generated against the running FastAPI OpenAPI schema. Target: **≥95%** of SDS §9 catalogue paths.

## Summary

| Area | SDS required | Present | Coverage |
| --- | --- | --- | --- |
| Health | `/health`, `/ready` | yes | 100% |
| Auth §9.2 | 5 endpoints | 5 | 100% |
| Users §9.3 | 2 | 2 | 100% |
| Documents §9.4 | 4 | 4 | 100% |
| OCR §9.5 | 4 | 4 | 100% |
| AI §9.6 | 7 (+ stream optional) | 8 (incl. `/ai/chat/stream`) | 100%+ |
| Pipelines §9.7 | 3 | 3 | 100% |
| Stats §9.8 | 3 + export P1 | 4 | 100% |
| Admin §9.9 | 8 | 8 | 100% |
| **Overall** | **~40 path ops** | **all required** | **≥95% ✓** |

## Path checklist

### Health
- [x] `GET /health`
- [x] `GET /ready`

### Auth `/api/v1/auth`
- [x] `POST /register`
- [x] `POST /login`
- [x] `POST /refresh`
- [x] `POST /logout`
- [x] `GET /csrf`

### Users `/api/v1/users`
- [x] `GET /me`
- [x] `PATCH /me`

### Documents `/api/v1/documents`
- [x] `POST /`
- [x] `GET /`
- [x] `GET /{document_id}`
- [x] `DELETE /{document_id}`

### OCR `/api/v1/ocr`
- [x] `POST /jobs`
- [x] `GET /jobs`
- [x] `GET /jobs/{job_id}`
- [x] `GET /jobs/{job_id}/results`

### AI `/api/v1/ai`
- [x] `POST /chat`
- [x] `POST /vision`
- [x] `GET /prompts`
- [x] `GET /prompts/{prompt_id}`
- [x] `POST /prompts` (admin)
- [x] `PATCH /prompts/{prompt_id}` (admin)
- [x] `POST /prompts/{prompt_id}/activate` (admin)
- [x] `POST /chat/stream` (extra vs SDS table — streaming P1)

### Pipelines `/api/v1/pipelines`
- [x] `POST /runs`
- [x] `GET /runs`
- [x] `GET /runs/{run_id}`

### Stats `/api/v1/stats`
- [x] `GET /daily`
- [x] `GET /monthly`
- [x] `GET /summary`
- [x] `GET /export` (P1)

### Admin `/api/v1/admin`
- [x] `GET /users`
- [x] `GET /users/{user_id}`
- [x] `PATCH /users/{user_id}`
- [x] `GET /usage`
- [x] `GET /ocr-history`
- [x] `GET /ocr-history/{job_id}`
- [x] `GET /audit-logs`
- [x] `GET /dashboard`

## Non-catalogue extras (OK)

- `GET /` — root probe
- `GET /api/v1/_probe/me`, `/api/v1/_probe/admin` — RBAC probes

## Gaps

None for SDS §9 v1 catalogue. Re-run review after adding endpoints:

```powershell
cd backend
python -c "from app.main import app; print('\n'.join(sorted(app.openapi()['paths'])))"
```
