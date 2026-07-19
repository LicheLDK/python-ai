# Copilot / Agent Instructions

- Read `/docs` (PRD.md, SDS.md, TASKS.md) before coding.
- No business logic in controllers (`backend/app/routers`).
- Service layer owns business logic (`backend/app/services`).
- Repository layer owns database access (`backend/app/repositories`).
- Stack: FastAPI + Next.js + PostgreSQL + Redis + Docker.
- Patterns: MVC + Service + Repository; dependency direction Controller → Service → Repository.
- Ask if the relevant spec is missing.
- Do not implement features without a TASKS.md task reference.
