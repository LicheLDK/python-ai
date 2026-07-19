# Staging up helper (T-12.01 / T-12.02)
param(
  [switch]$SkipSeed,
  [switch]$Build
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$envFile = Join-Path $root ".env.staging"
$example = Join-Path $root ".env.staging.example"
if (-not (Test-Path $envFile)) {
  if (-not (Test-Path $example)) { throw "missing .env.staging.example" }
  Copy-Item $example $envFile
  Write-Host "Created .env.staging from example — edit secrets before production use."
}

$compose = @("-f", "docker-compose.staging.yml", "--env-file", ".env.staging")
if ($Build) {
  docker compose @compose up --build -d
} else {
  docker compose @compose up -d
}

Write-Host "Running migrate..."
docker compose @compose --profile tools run --rm migrate

if (-not $SkipSeed) {
  Write-Host "Running seed..."
  docker compose @compose --profile tools run --rm seed
}

Write-Host ""
Write-Host "Staging up. API http://localhost:18000  Web http://localhost:13000"
Write-Host "Smoke: `$env:API_BASE='http://localhost:18000'; powershell -File scripts/smoke.ps1"
