#!/usr/bin/env sh
# Alembic upgrade wrapper. docs/TASKS.md T-0.06 / T-0.11
# Requires repo-root `.env` (copy from `.env.example`).
# Host port must match docker-compose publish (default localhost:5433).
set -e
cd "$(dirname "$0")/../backend"
python -m alembic upgrade head
python -m alembic current
