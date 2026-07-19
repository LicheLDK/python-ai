#!/bin/sh
# Backend container entrypoint (T-0.08).
# Wait for PostgreSQL and Redis before starting the main process.
set -e

MAX_ATTEMPTS="${WAIT_FOR_DEPS_MAX_ATTEMPTS:-60}"
SLEEP_SECONDS="${WAIT_FOR_DEPS_SLEEP_SECONDS:-2}"

log() {
  echo "[entrypoint] $*"
}

wait_for_tcp() {
  # Usage: wait_for_tcp <host> <port> <label>
  host="$1"
  port="$2"
  label="$3"
  attempt=1

  log "waiting for ${label} at ${host}:${port} (max ${MAX_ATTEMPTS} attempts)"
  while [ "$attempt" -le "$MAX_ATTEMPTS" ]; do
    if python -c "import socket,sys; s=socket.create_connection(('${host}', int('${port}')), 2); s.close()" 2>/dev/null; then
      log "${label} is reachable"
      return 0
    fi
    log "attempt ${attempt}/${MAX_ATTEMPTS}: ${label} not ready yet"
    attempt=$((attempt + 1))
    sleep "$SLEEP_SECONDS"
  done

  log "ERROR: timed out waiting for ${label} (${host}:${port})"
  return 1
}

# Optional skip for local debugging: WAIT_FOR_DEPS=0
if [ "${WAIT_FOR_DEPS:-1}" = "0" ]; then
  log "WAIT_FOR_DEPS=0 ??skipping dependency wait"
  exec "$@"
fi

# Prefer explicit hosts; fall back to Compose service names.
PG_HOST="${POSTGRES_HOST:-postgres}"
PG_PORT="${POSTGRES_PORT:-5432}"
REDIS_HOST="${REDIS_HOST:-redis}"
REDIS_PORT="${REDIS_PORT:-6379}"

wait_for_tcp "$PG_HOST" "$PG_PORT" "PostgreSQL"
wait_for_tcp "$REDIS_HOST" "$REDIS_PORT" "Redis"

log "dependencies ready ??starting: $*"
exec "$@"


