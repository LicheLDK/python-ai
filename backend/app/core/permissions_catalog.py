"""Canonical permission codes (T-2.01 / PRD § RBAC P1 examples).

Seeded by Alembic 0003_rbac. Enforcement helpers are T-2.05 (P1).
"""

from __future__ import annotations

# (code, description)
PERMISSION_SEED: tuple[tuple[str, str], ...] = (
    ("ocr:run", "Submit and view own OCR jobs"),
    ("ai:chat", "Call AI chat endpoints"),
    ("ai:vision", "Call AI vision endpoints"),
    ("ai:manage_prompts", "Create/activate AI prompt templates"),
    ("documents:write", "Upload and delete own documents"),
    ("admin:users", "Manage users (admin console)"),
    ("admin:audit", "View audit logs"),
    ("admin:usage", "View global AI/OCR usage"),
)

# Codes granted to role=user (admin receives all codes).
USER_ROLE_PERMISSION_CODES: tuple[str, ...] = (
    "ocr:run",
    "ai:chat",
    "ai:vision",
    "documents:write",
)
