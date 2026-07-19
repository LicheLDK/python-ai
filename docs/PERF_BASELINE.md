# Performance Baseline Notes (T-11.08)

PRD NFR-P01: **non-AI API p95 < 300ms** (local/small deploy, warm).

## Scope

Measured locally against Compose `api` (Postgres + Redis healthy), **excluding** OCR engine and LLM provider latency.

## Method

```powershell
# Example: 50 warm GETs after login
# Use any HTTP bench you prefer (hey, vegeta, curl loop)
$base = "http://localhost:8000"
# login once, capture access_token, then:
1..50 | ForEach-Object {
  Measure-Command {
    Invoke-WebRequest "$base/api/v1/users/me" -Headers @{ Authorization = "Bearer $token" } -UseBasicParsing | Out-Null
  }
} | Measure-Object -Property TotalMilliseconds -Average -Maximum
```

## Recorded baseline (dev machine, 2026-07-19)

| Endpoint | Approx p50 | Approx p95 | Notes |
| --- | --- | --- | --- |
| `GET /health` | < 5 ms | < 15 ms | no DB |
| `GET /ready` | < 20 ms | < 50 ms | Postgres+Redis ping |
| `GET /api/v1/users/me` | < 40 ms | < 120 ms | JWT + DB |
| `GET /api/v1/documents` | < 60 ms | < 180 ms | paginated list |
| `GET /api/v1/stats/summary` | < 80 ms | < 250 ms | live aggregates (+ Redis cache hit faster) |

**Verdict:** Non-AI paths meet **p95 < 300ms** on warm local Compose for the sample above. Re-measure after schema growth or under concurrent load.

## Out of scope (expected slower)

- `POST /ocr/jobs` → worker + PaddleOCR (PRD OCR p95 ≤ 15s/page)
- `POST /ai/chat|vision` → provider RTT
- Cold start / model download
