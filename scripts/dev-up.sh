#!/usr/bin/env sh
# Compose up wrapper (boilerplate). docs/TASKS.md T-0.11
set -e
cd "$(dirname "$0")/.."
docker compose up --build "$@"
