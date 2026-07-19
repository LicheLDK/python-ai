"""Idempotent OCR-analysis prompt seed pack (T-5.09).

Run: ``python -m app.scripts.seed_prompts`` from ``backend/``.
"""

from __future__ import annotations

import sys
from typing import Any

from app.core.database import SessionLocal
from app.repositories.ai_prompt_repository import AiPromptRepository

# Default prompts for Phase 6 pipeline AI stage.
SEED_PROMPTS: list[dict[str, Any]] = [
    {
        "name": "ocr.analyze.summary",
        "template": (
            "You are an OCR analysis assistant. Summarize the following document "
            "text clearly in Korean when the source is Korean, otherwise in the "
            "source language.\n\n"
            "Focus on: document type, key entities, amounts/dates, and action items.\n"
            "OCR text:\n{ocr_text}"
        ),
        "variables_schema": {
            "type": "object",
            "required": ["ocr_text"],
            "properties": {"ocr_text": {"type": "string"}},
        },
        "activate": True,
    },
    {
        "name": "ocr.analyze.extract_fields",
        "template": (
            "Extract structured fields from the OCR text as JSON only "
            "(no markdown). Include keys that appear in the text such as "
            "title, date, parties, amounts, and notes.\n\n"
            "OCR text:\n{ocr_text}"
        ),
        "variables_schema": {
            "type": "object",
            "required": ["ocr_text"],
            "properties": {"ocr_text": {"type": "string"}},
        },
        "activate": True,
    },
    {
        "name": "vision.document.describe",
        "template": (
            "Describe this document image. Note layout, headings, stamps, "
            "and any readable text. Respond in Korean if the document appears "
            "Korean."
        ),
        "variables_schema": {},
        "activate": True,
    },
]


def seed_prompts() -> int:
    session = SessionLocal()
    try:
        repo = AiPromptRepository(session)
        created = 0
        skipped = 0
        for spec in SEED_PROMPTS:
            name = spec["name"]
            existing = repo.get_by_name_version(name, 1)
            if existing is not None:
                skipped += 1
                print(f"seed: prompt already present, skipping: {name}@v1")
                continue
            if spec.get("activate"):
                repo.deactivate_active_for_name(name)
            repo.create(
                name=name,
                version=1,
                template=spec["template"],
                variables_schema=spec.get("variables_schema") or {},
                active=bool(spec.get("activate")),
                created_by=None,
            )
            created += 1
            print(f"seed: created prompt {name}@v1 active={bool(spec.get('activate'))}")
        session.commit()
        print(f"seed: prompts done created={created} skipped={skipped}")
        return 0
    except Exception as exc:  # noqa: BLE001 — CLI exit path
        session.rollback()
        print(f"seed: prompts failed: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()


def main() -> None:
    raise SystemExit(seed_prompts())


if __name__ == "__main__":
    main()
