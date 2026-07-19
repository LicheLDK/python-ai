# Compose smoke (T-11.02) — PowerShell twin of scripts/smoke.sh
param(
  [string]$ApiBase = $(if ($env:API_BASE) { $env:API_BASE } else { "http://localhost:8000" }),
  [switch]$Upload
)

$ErrorActionPreference = "Stop"
$email = "smoke-$(Get-Date -Format 'yyyyMMddHHmmss')-$PID@example.com"
$password = "Str0ng-P@ss!"
$name = "Smoke User"

Write-Host "== smoke against $ApiBase =="

Write-Host "1) GET /health"
$h = Invoke-RestMethod "$ApiBase/health"
if (-not $h.status) { throw "health missing status" }
Write-Host "   ok"

Write-Host "2) GET /ready"
$r = Invoke-RestMethod "$ApiBase/ready"
if (-not $r.postgres) { throw "ready missing postgres" }
Write-Host "   ok"

Write-Host "3) POST /api/v1/auth/register ($email)"
Invoke-RestMethod -Method Post "$ApiBase/api/v1/auth/register" `
  -ContentType "application/json" `
  -Body (@{ email = $email; password = $password; name = $name } | ConvertTo-Json) | Out-Null
Write-Host "   ok"

Write-Host "4) POST /api/v1/auth/login"
$login = Invoke-RestMethod -Method Post "$ApiBase/api/v1/auth/login" `
  -ContentType "application/json" `
  -Body (@{ email = $email; password = $password } | ConvertTo-Json)
if (-not $login.access_token) { throw "login missing access_token" }
$token = $login.access_token
Write-Host "   ok"

Write-Host "5) GET /api/v1/users/me"
$me = Invoke-RestMethod "$ApiBase/api/v1/users/me" `
  -Headers @{ Authorization = "Bearer $token" }
if ($me.email -ne $email) { throw "me email mismatch" }
Write-Host "   ok"

$doUpload = $Upload -or ($env:SMOKE_UPLOAD -eq "1")
if ($doUpload) {
  $fixture = if ($env:SMOKE_FIXTURE) {
    $env:SMOKE_FIXTURE
  } else {
    Join-Path $PSScriptRoot "..\backend\app\tests\fixtures\sample_ocr_text.png"
  }
  if (-not (Test-Path $fixture)) {
    Write-Host "6) skip upload — fixture missing: $fixture"
  } else {
    Write-Host "6) POST /api/v1/documents (optional upload)"
    # Prefer curl.exe multipart (works on Windows PowerShell 5.1).
    $raw = & curl.exe -sf -X POST "$ApiBase/api/v1/documents" `
      -H "Authorization: Bearer $token" `
      -F "file=@$fixture;type=image/png"
    if ($LASTEXITCODE -ne 0 -or ($raw -notmatch '"filename"')) {
      throw "upload failed: $raw"
    }
    Write-Host "   ok"
  }
} else {
  Write-Host "6) upload skipped (pass -Upload or SMOKE_UPLOAD=1)"
}

Write-Host ""
Write-Host "smoke ok"
