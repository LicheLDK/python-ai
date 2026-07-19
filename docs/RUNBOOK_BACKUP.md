# Runbook — Backup / Restore (T-11.07)

Volumes from `docker-compose.yml`:

| Volume | Purpose |
| --- | --- |
| `aisaas_pgdata` | PostgreSQL data |
| `aisaas_redisdata` | Redis AOF (ephemeral OK for v1 denylist/queue) |
| `aisaas_storage` | Document binaries (`STORAGE_PATH`) |

## Backup (Postgres + storage)

```powershell
# From repo root, with stack running
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
New-Item -ItemType Directory -Force -Path ".\backups\$stamp" | Out-Null

# Logical Postgres dump
docker compose exec -T postgres pg_dump -U aisaas -d ai_saas -Fc > ".\backups\$stamp\ai_saas.dump"

# Storage volume (documents)
docker run --rm -v aisaas_storage:/data -v ${PWD}/backups/${stamp}:/out alpine `
  tar czf /out/storage.tgz -C /data .
```

Redis: optional; safe to skip for v1 (jobs re-enqueue, denylist resets).

## Restore

```powershell
# Stop writers
docker compose stop api worker web

# Restore DB (destroys current DB contents for ai_saas)
Get-Content ".\backups\<stamp>\ai_saas.dump" -AsByteStream |
  docker compose exec -T postgres pg_restore -U aisaas -d ai_saas --clean --if-exists

# Restore storage
docker run --rm -v aisaas_storage:/data -v ${PWD}/backups/<stamp>:/in alpine `
  sh -c "rm -rf /data/* && tar xzf /in/storage.tgz -C /data"

docker compose start api worker web
docker compose exec api python -m alembic upgrade head
```

## Notes

- Prefer scheduled dumps before migrations
- Test restore on a disposable Compose project before production use
- Keep dumps off the app volume (host `./backups/` is gitignored ideally)
