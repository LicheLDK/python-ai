#!/usr/bin/env sh
# Staging up helper (T-12.01 / T-12.02)
set -e
cd "$(dirname "$0")/.."

if [ ! -f .env.staging ]; then
  cp .env.staging.example .env.staging
  echo "Created .env.staging from example — edit secrets before shared use."
fi

COMPOSE="docker compose -f docker-compose.staging.yml --env-file .env.staging"

$COMPOSE up --build -d
$COMPOSE --profile tools run --rm migrate
$COMPOSE --profile tools run --rm seed

echo
echo "Staging up. API http://localhost:18000  Web http://localhost:13000"
echo "Smoke: API_BASE=http://localhost:18000 ./scripts/smoke.sh"
