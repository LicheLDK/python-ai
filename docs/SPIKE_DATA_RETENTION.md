# Spike: Data Retention & Erasure API (T-11.09 / P1 → Phase 17)

**Status:** **Implemented (Phase 17 MVP)** — retention cron still deferred.  
**Goal:** GDPR-style account/document erasure.

## Drivers

- User requests deletion of account and uploaded documents
- Admin-initiated purge of inactive users
- Storage + DB growth control

## Implemented scopes (Phase 17)

| Scope | Behavior |
| --- | --- |
| Document erase | Soft-delete already exists (`status=deleted`); hard-delete removes storage object + OCR/pipeline/RAG rows (CASCADE) |
| Account erase | Anonymize `users` email/name + inactive; revoke refresh tokens; hard-delete owned documents; **audit logs retained** (`actor_id` SET NULL on user delete — we keep anonymized user row) |

## API (live)

```
DELETE /api/v1/users/me/data                 # self-service (scopes=account → +documents)
GET    /api/v1/users/me/erasure-jobs/{id}
POST   /api/v1/admin/erasure-jobs            # { user_id, scopes[] }
GET    /api/v1/admin/erasure-jobs/{id}
```

Worker: `run_erasure_job` (ARQ). Migration: `0013_erasure_jobs`.

## Still deferred

1. Retention cron: purge `stat_daily` older than N days; purge soft-deleted documents after M days
2. Audit log hard delete / payload scrub (compliance may require retain — MVP retains)
3. LLM provider logs are out-of-band — erasure is **local SoR only**
4. Org-scoped bulk erasure beyond target user

## Exit

Phase 17 MVP shipped; see `docs/TASKS.md` Phase 17 and `usage.md`.
