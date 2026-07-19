#!/bin/sh
# Frontend container entrypoint (T-0.09).
set -e
echo "[web-entrypoint] starting: $*"
exec "$@"
