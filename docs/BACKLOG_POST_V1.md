# Post-v1 Backlog (T-12.05)

Imported from [PRD §5.3 Future Candidates](PRD.md#53-future-candidates-post-v1) and open engineering spikes.

| ID | Phase | Candidate | Notes / links |
| --- | --- | --- | --- |
| B-1.1-RAG | v1.1 | RAG — embeddings store, retrieval, citations | **Phase 15 Done** — JSONB chunks + EmbeddingPort + chat citations |
| B-1.1-OLLAMA | v1.1 | Ollama local LLM | **Phase 13 Done** — `OllamaAdapter` + factory + compose profile |
| B-1.2-TENANT | v1.2 | Soft multi-tenant (`org_id`, quotas, branding) | **Phase 16 Done** — orgs + users.org_id + org AI quota; branding JSONB bag |
| B-2.0-SCALE | v2.0 | Worker scale-out / optional service split | Compose worker already separate process |
| B-LATER-K8S | Later | K8s Helm charts | PRD Non-Goal for v1 |
| B-LATER-EVENT | Later | Event-driven pipeline bus | Beyond ARQ queue |
| B-P1-S3 | P1+ | Object storage (S3-compatible) behind `StoragePort` | **Phase 14 Done** — `S3StorageAdapter` + factory + MinIO profile |
| B-P1-ERASURE | P1+ | Account/document erasure APIs | [SPIKE_DATA_RETENTION.md](SPIKE_DATA_RETENTION.md) |
| B-P1-FALLBACK | P1+ | Dual-provider automatic failover | Flag exists; harden ops alerts |

## Suggested next implementation order

1. ~~Ollama factory wiring (finish stub)~~ → **Done (Phase 13)**  
2. ~~S3 storage adapter (same `StoragePort`)~~ → **Done (Phase 14)**  
3. ~~RAG minimal interface + one store~~ → **Done (Phase 15)**  
4. ~~Soft tenant + org quota~~ → **Done (Phase 16)**  
5. Erasure job APIs  

Track new work as TASKS IDs under a future Phase 17+ section when scheduling starts.
