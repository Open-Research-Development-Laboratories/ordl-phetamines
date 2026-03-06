param(
  [switch]$SkipFrontendBuild,
  [switch]$SkipFleetTests
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path

Write-Host "== ORDL Release Gate =="
Write-Host "Repo: $repoRoot"

function Invoke-Step {
  param(
    [string]$Name,
    [scriptblock]$Script
  )
  Write-Host ""
  Write-Host ">> $Name"
  & $Script
}

Invoke-Step -Name "Backend tests (ordl_platform/backend)" -Script {
  Push-Location (Join-Path $repoRoot "ordl_platform\\backend")
  try {
    python -m pytest -q
  } finally {
    Pop-Location
  }
}

if (-not $SkipFleetTests) {
  Invoke-Step -Name "Fleet API tests (fleet_api/tests)" -Script {
    Push-Location $repoRoot
    try {
      python -m pytest -q fleet_api/tests
    } finally {
      Pop-Location
    }
  }
}

if (-not $SkipFrontendBuild) {
  Invoke-Step -Name "Frontend build (ordl_platform/frontend)" -Script {
    Push-Location (Join-Path $repoRoot "ordl_platform\\frontend")
    try {
      npm run build
    } finally {
      Pop-Location
    }
  }
}

Write-Host ""
Write-Host "Release gate passed."
