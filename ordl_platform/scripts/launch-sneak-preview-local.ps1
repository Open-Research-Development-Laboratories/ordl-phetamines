param(
  [switch]$SkipReleaseGate,
  [switch]$SkipBootstrap,
  [string]$ApiBase = "http://127.0.0.1:8891/v1",
  [string]$UiUrl = "http://127.0.0.1:5173"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
$preflightScript = Join-Path $repoRoot "ordl_platform\\scripts\\sneak-preview-preflight.ps1"
$startDevScript = Join-Path $repoRoot "ordl_platform\\scripts\\start-dev.ps1"
$bootstrapPilotScript = Join-Path $repoRoot "ordl_platform\\scripts\\bootstrap-ordl-pilot.ps1"
$bootstrapStandardsScript = Join-Path $repoRoot "ordl_platform\\scripts\\bootstrap-adopted-standards.ps1"

function Wait-ApiHealth {
  param(
    [string]$HealthUrl,
    [int]$TimeoutSeconds = 90
  )
  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    try {
      $res = Invoke-RestMethod -Method Get -Uri $HealthUrl -TimeoutSec 4
      if ($res.status -eq "ok") { return $true }
    } catch {
      Start-Sleep -Seconds 2
    }
  }
  return $false
}

Write-Host "== ORDL Local Sneak Preview Launch =="

$preflightArgs = @(
  "-ExecutionPolicy", "Bypass",
  "-File", $preflightScript,
  "-PreviewMode", "local"
)
if ($SkipReleaseGate) { $preflightArgs += "-SkipReleaseGate" }
powershell @preflightArgs

Write-Host ""
Write-Host "Starting local API/UI shells..."
powershell -ExecutionPolicy Bypass -File $startDevScript -Api -Ui

$healthUrl = "$($ApiBase.TrimEnd('/v1'))/health"
Write-Host "Waiting for API health at $healthUrl ..."
if (-not (Wait-ApiHealth -HealthUrl $healthUrl -TimeoutSeconds 90)) {
  throw "API health check timed out. Ensure backend shell started cleanly."
}

if (-not $SkipBootstrap) {
  Write-Host ""
  Write-Host "Bootstrapping pilot principals and standards..."
  powershell -ExecutionPolicy Bypass -File $bootstrapPilotScript -ApiBase $ApiBase
  powershell -ExecutionPolicy Bypass -File $bootstrapStandardsScript -ApiBase $ApiBase
}

Write-Host ""
Write-Host "Local sneak preview is up."
Write-Host "UI:  $UiUrl"
Write-Host "API: $ApiBase"
