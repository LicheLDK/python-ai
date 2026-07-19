# Deployment Runbook (T-12.02)

Order is normative: **migrate → api → worker → web**.  
Never start API traffic against a schema behind `alembic head`.

## Local (dev)

```powershell
Copy-Item .env.example .env   # once
docker compose up --build -d
# Host migrate if needed:
cd backend; python -m alembic upgrade head
# or: bash scripts/migrate.sh
powershell -File scripts/smoke.ps1
```

| URL | Service |
| --- | --- |
| http://localhost:8000 | API |
| http://localhost:3000 | Web |
| localhost:5433 | Postgres (published) |
| localhost:6379 | Redis (published) |

## Staging (T-12.01)

```powershell
Copy-Item .env.staging.example .env.staging
# Edit .env.staging — set POSTGRES_PASSWORD, JWT_SECRET, SEED_ADMIN_*, API keys

# 1) Infra + app images (api/worker/web wait for healthy postgres/redis)
docker compose -f docker-compose.staging.yml --env-file .env.staging up --build -d

# 2) Migrate (one-shot)
docker compose -f docker-compose.staging.yml --env-file .env.staging --profile tools run --rm migrate

# 3) Seed admin + prompts (optional, idempotent)
docker compose -f docker-compose.staging.yml --env-file .env.staging --profile tools run --rm seed

# 4) Verify
$env:API_BASE="http://localhost:18000"
powershell -File scripts/smoke.ps1
```

| URL | Service |
| --- | --- |
| http://localhost:18000 | Staging API |
| http://localhost:13000 | Staging Web |
| (none) | Postgres/Redis — internal only |

### Why this order

1. **migrate** — schema must match models before API/worker queries
2. **api** — serves HTTP; entrypoint waits for TCP to postgres/redis
3. **worker** — consumes ARQ jobs; same image, needs migrated tables + storage volume
4. **web** — browser client; needs API origin (`NEXT_PUBLIC_API_BASE_URL`) already reachable

### Rolling update (staging)

```powershell
# Pull/build new images
docker compose -f docker-compose.staging.yml --env-file .env.staging build api worker web

# Migrate first
docker compose -f docker-compose.staging.yml --env-file .env.staging --profile tools run --rm migrate

# Recreate app processes
docker compose -f docker-compose.staging.yml --env-file .env.staging up -d --no-deps --force-recreate api worker web
```

### Rollback notes

- Prefer forward-fix Alembic migrations; if rollback required: `alembic downgrade -1` only after confirming data safety
- Restore DB/storage from [RUNBOOK_BACKUP.md](RUNBOOK_BACKUP.md) if migration corrupts data
- Keep previous image tags for quick `image:` pin rollback

### Operator dry-run checklist

- [ ] `.env.staging` has no placeholder `CHANGE_ME_*` left
- [ ] `migrate` exits 0
- [ ] `GET /health` and `GET /ready` on staging API
- [ ] Smoke register/login succeeds
- [ ] Worker logs show ARQ started (no crash loop)
- [ ] Web loads login at staging web port
