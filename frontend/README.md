# Frontend (Next.js) — Phase 8/9

## Env

| Variable | Default | Notes |
| --- | --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | Browser-facing API origin (Compose `web` service sets this) |

Copy from repo root `.env.example`. CORS on the API must include the web origin (`http://localhost:3000`) with credentials.

## Scripts

```bash
cd frontend
npm install
npm run dev      # http://localhost:3000
npm run lint
npm run build
```

## Auth notes

- Access token: in-memory only (`lib/auth.ts`, ADR-029)
- Refresh: HttpOnly cookie + `X-CSRF-Token` on `/api/v1/auth/refresh|logout`
- `services/http.ts` retries once after refresh on 401
