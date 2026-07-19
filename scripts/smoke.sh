#!/usr/bin/env sh
# Compose smoke (T-0.11 / T-11.02): health → ready → register → login → (optional) upload
set -e
API_BASE="${API_BASE:-http://localhost:8000}"
SMOKE_UPLOAD="${SMOKE_UPLOAD:-0}"
EMAIL="smoke-$(date +%s)-$$@example.com"
PASSWORD="Str0ng-P@ss!"
NAME="Smoke User"

echo "== smoke against ${API_BASE} =="

echo "1) GET /health"
curl -sf "${API_BASE}/health" | grep -q '"status"'
echo "   ok"

echo "2) GET /ready"
curl -sf "${API_BASE}/ready" | grep -q '"postgres"'
echo "   ok"

echo "3) POST /api/v1/auth/register (${EMAIL})"
curl -sf -X POST "${API_BASE}/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\",\"name\":\"${NAME}\"}" \
  | grep -q '"email"'
echo "   ok"

echo "4) POST /api/v1/auth/login"
LOGIN_JSON=$(curl -sf -X POST "${API_BASE}/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}" \
  -c /tmp/aisaas-smoke-cookies.txt)
echo "${LOGIN_JSON}" | grep -q '"access_token"'
ACCESS=$(echo "${LOGIN_JSON}" | sed -n 's/.*"access_token"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
test -n "${ACCESS}"
echo "   ok"

echo "5) GET /api/v1/users/me"
curl -sf "${API_BASE}/api/v1/users/me" \
  -H "Authorization: Bearer ${ACCESS}" \
  | grep -q "${EMAIL}"
echo "   ok"

if [ "${SMOKE_UPLOAD}" = "1" ]; then
  FIXTURE="${SMOKE_FIXTURE:-backend/app/tests/fixtures/sample_ocr_text.png}"
  if [ ! -f "${FIXTURE}" ]; then
    echo "   skip upload — fixture missing: ${FIXTURE}"
  else
    echo "6) POST /api/v1/documents (optional upload)"
    curl -sf -X POST "${API_BASE}/api/v1/documents" \
      -H "Authorization: Bearer ${ACCESS}" \
      -F "file=@${FIXTURE};type=image/png" \
      | grep -q '"filename"'
    echo "   ok"
  fi
else
  echo "6) upload skipped (set SMOKE_UPLOAD=1 to enable)"
fi

echo
echo "smoke ok"
