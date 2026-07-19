# Spike: Data Retention & Erasure API (T-11.09 / P1)

**Status:** Design spike only — **not implemented in v1**.  
**Goal:** Outline GDPR-style account/document erasure without coding it now.

## Drivers

- User requests deletion of account and uploaded documents
- Admin-initiated purge of inactive users
- Storage + DB growth control

## Proposed scopes (v1.1+)

| Scope | Behavior |
| --- | --- |
| Document erase | Soft-delete already exists (`status=deleted`); hard-delete removes storage object + OCR/pipeline rows |
| Account erase | Anonymize `users` email/name; cascade or null `actor_id` on audit; delete documents/OCR/AI owned rows |
| Retention job | Cron: purge `stat_daily` older than N days; purge soft-deleted documents after M days |

## Candidate API (future)

```
DELETE /api/v1/users/me/data          # self-service erasure request
POST   /api/v1/admin/erasure-jobs     # admin: { user_id, scopes[] }
GET    /api/v1/admin/erasure-jobs/{id}
```

## Open decisions

1. Hard vs soft delete for audit logs (compliance may require retain)
2. LLM provider logs are out-of-band — document that erasure is local SoR only
3. Soft multi-tenant (`org_id`) interaction if added later

## Exit

Spike filed; implementation deferred to post-v1 backlog (see Phase 12 / PRD §5.3).
