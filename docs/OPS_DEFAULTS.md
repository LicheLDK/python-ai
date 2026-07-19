# Ops Defaults — Rate Limits & Quotas (T-11.06)

Tune via env; defaults match `backend/app/core/constants.py` / `Settings`.

## Auth login rate limit

| Setting | Default | Env |
| --- | --- | --- |
| Max attempts | 10 | (constant; bump in code if needed) |
| Window | 15 minutes | — |
| Keys | email + IP | Redis `aisaas:rl:login:*` |
| Response | 429 envelope | |

## AI request rate limit (per user)

| Setting | Default | Env |
| --- | --- | --- |
| Max requests | 60 | `AI_RATE_LIMIT_MAX` / `ai_rate_limit_max` |
| Window | 60 seconds | `AI_RATE_LIMIT_WINDOW_SECONDS` |
| Key | `aisaas:rl:ai:{user_id}` | |
| Response | 429 | |

## Upload

| Setting | Default | Env |
| --- | --- | --- |
| Max bytes | 10_485_760 (10 MiB) | `UPLOAD_MAX_BYTES` |
| MIME | jpeg/png/webp/pdf | code allowlist |

## OCR

| Setting | Default | Env |
| --- | --- | --- |
| Stale queued | 180s | `OCR_STALE_QUEUED_SECONDS` |
| Stale running | 1200s | `OCR_STALE_RUNNING_SECONDS` |
| Page limit | product default | document/service checks |

## Stats

| Setting | Default | Env |
| --- | --- | --- |
| Materialize cron | every 10m | `STATS_MATERIALIZE_ENABLED` |
| Summary cache TTL | 300s | `STATS_SUMMARY_CACHE_SECONDS` |

## Recommended staging starting points

- AI: 30 req / 60s per user if cost-sensitive
- Login: keep 10 / 15m; alert on sustained 429s
- Upload: keep 10 MiB until object storage (S3) lands
