#!/usr/bin/env sh
# Seed default admin (T-1.07) + OCR-analysis prompts (T-5.09).
# Requires repo-root `.env` with SEED_ADMIN_* (see .env.example).
set -e
cd "$(dirname "$0")/../backend"
python -m app.scripts.seed_admin
python -m app.scripts.seed_prompts
