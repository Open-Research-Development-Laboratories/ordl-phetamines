param(
  [string]$RepoRoot = "",
  [string]$ApiKey = $env:FLEET_API_KEY,
  [string]$SshPassword = $env:FLEET_SSH_PASSWORD,
  [int]$ApiPort = 8890
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
  $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

$runPy = Join-Path $RepoRoot "fleet_api\run.py"
$stateDir = Join-Path $RepoRoot "fleet_api\state"
$logFile = Join-Path $stateDir "fleet-api.log"
$errFile = Join-Path $stateDir "fleet-api.err.log"

if (!(Test-Path $runPy)) {
  throw "run.py not found: $runPy"
}

New-Item -ItemType Directory -Force -Path $stateDir | Out-Null

$listener = Get-NetTCPConnection -State Listen -LocalPort $ApiPort -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
  Write-Host "Fleet API appears to be running (port $ApiPort already listening by PID $($listener.OwningProcess))."
  exit 0
}

$already = Get-CimInstance Win32_Process |
  Where-Object {
    $_.Name -match "python" -and
    $_.CommandLine -and
    (
      $_.CommandLine -match "fleet_api[\\\/]run.py" -or
      $_.CommandLine -match "(^|\\s)run.py(\\s|$)"
    )
  } | Select-Object -First 1
if ($already) {
  Write-Host "Fleet API process already running (PID $($already.ProcessId))."
  exit 0
}

if (-not $ApiKey) {
  throw "FLEET_API_KEY is required."
}
if (-not $SshPassword) {
  throw "FLEET_SSH_PASSWORD is required."
}

$env:FLEET_API_KEY = $ApiKey
$env:FLEET_SSH_PASSWORD = $SshPassword
$env:FLEET_WORKSPACE_ROOT = "C:\development"

Push-Location (Join-Path $RepoRoot "fleet_api")
try {
  Start-Process -FilePath "python" `
    -ArgumentList @("run.py") `
    -WorkingDirectory (Join-Path $RepoRoot "fleet_api") `
    -WindowStyle Hidden `
    -RedirectStandardOutput $logFile `
    -RedirectStandardError $errFile
}
finally {
  Pop-Location
}

Write-Host "Fleet API start command submitted."
