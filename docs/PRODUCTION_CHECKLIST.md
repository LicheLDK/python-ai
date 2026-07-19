# Production / Staging Readiness Checklist (Phase 11 exit)

Link pack for operators before Phase 12 release gate.

- [ ] CI green on main (`.github/workflows/ci.yml`)
- [ ] Smoke: `scripts/smoke.sh` (optional `SMOKE_UPLOAD=1`)
- [ ] OpenAPI coverage ≥95%: [OPENAPI_COVERAGE.md](OPENAPI_COVERAGE.md)
- [ ] PR template layer rules used: `.github/PULL_REQUEST_TEMPLATE.md`
- [ ] Security: [SECURITY_HARDENING.md](SECURITY_HARDENING.md)
- [ ] Rate-limit defaults understood: [OPS_DEFAULTS.md](OPS_DEFAULTS.md)
- [ ] Backup dry-run: [RUNBOOK_BACKUP.md](RUNBOOK_BACKUP.md)
- [ ] Perf baseline reviewed: [PERF_BASELINE.md](PERF_BASELINE.md)
- [ ] Erasure spike acknowledged (deferred): [SPIKE_DATA_RETENTION.md](SPIKE_DATA_RETENTION.md)
- [ ] Admin QA: [QA_ADMIN_CHECKLIST.md](QA_ADMIN_CHECKLIST.md)
- [ ] Staging compose boots: [RUNBOOK_DEPLOY.md](RUNBOOK_DEPLOY.md)
- [ ] Release gate signed: [RELEASE_GATE.md](RELEASE_GATE.md)
- [ ] Changelog reviewed: [../CHANGELOG.md](../CHANGELOG.md)
- [ ] Post-v1 backlog visible: [BACKLOG_POST_V1.md](BACKLOG_POST_V1.md)
