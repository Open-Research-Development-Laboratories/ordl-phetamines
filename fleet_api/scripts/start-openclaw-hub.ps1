param(
  [string]$RepoRoot = "C:\Users\Winsock\Documents\GitHub\ordl-phetamines",
  [string]$Bind = "lan"
)

$ErrorActionPreference = "Stop"

$stateDir = Join-Path $RepoRoot "fleet_api\state"
$logFile = Join-Path $stateDir "openclaw-hub.log"
$errFile = Join-Path $stateDir "openclaw-hub.err.log"
New-Item -ItemType Directory -Force -Path $stateDir | Out-Null

$openclawCmd = $null
$cmdExe = Get-Command openclaw.cmd -ErrorAction SilentlyContinue
if ($cmdExe) {
  $openclawCmd = "`"$($cmdExe.Source)`""
}
if (-not $openclawCmd) {
  $candidate = "$env:APPDATA\npm\openclaw.cmd"
  if (Test-Path $candidate) { $openclawCmd = "`"$candidate`"" }
}
if (-not $openclawCmd) {
  $cmd = Get-Command openclaw -ErrorAction SilentlyContinue
  if ($cmd) { $openclawCmd = "openclaw" }
}
if (-not $openclawCmd) {
  throw "openclaw binary not found."
}

$listener = Get-NetTCPConnection -State Listen -LocalPort 18789 -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
  Write-Host "OpenClaw gateway appears to be running (port 18789 listening by PID $($listener.OwningProcess))."
  exit 0
}

$already = Get-CimInstance Win32_Process |
  Where-Object {
    $_.Name -match "openclaw|openclaw-gateway|node" -and
    $_.CommandLine -and
    ($_.CommandLine -match "openclaw-gateway" -or $_.CommandLine -match "openclaw.*gateway\\s+run")
  } | Select-Object -First 1

if ($already) {
  Write-Host "OpenClaw gateway already running process detected (PID $($already.ProcessId))."
  exit 0
}

Start-Process -FilePath "cmd.exe" `
  -ArgumentList @("/c", "$openclawCmd gateway run --bind $Bind") `
  -WorkingDirectory $stateDir `
  -WindowStyle Hidden `
  -RedirectStandardOutput $logFile `
  -RedirectStandardError $errFile

Write-Host "OpenClaw gateway start command submitted."
