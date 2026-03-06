param(
  [string]$RepoRoot = "C:\Users\Winsock\Documents\GitHub\ordl-phetamines",
  [string]$Bind = "lan"
)

$ErrorActionPreference = "Stop"

$stateDir = Join-Path $RepoRoot "fleet_api\state"
$logFile = Join-Path $stateDir "ordlctl-hub.log"
$errFile = Join-Path $stateDir "ordlctl-hub.err.log"
New-Item -ItemType Directory -Force -Path $stateDir | Out-Null

$ordlctlCmd = $null
$cmdExe = Get-Command ordlctl.cmd -ErrorAction SilentlyContinue
if ($cmdExe) {
  $ordlctlCmd = "`"$($cmdExe.Source)`""
}
if (-not $ordlctlCmd) {
  $candidate = "$env:APPDATA\npm\ordlctl.cmd"
  if (Test-Path $candidate) { $ordlctlCmd = "`"$candidate`"" }
}
if (-not $ordlctlCmd) {
  $cmd = Get-Command ordlctl -ErrorAction SilentlyContinue
  if ($cmd) { $ordlctlCmd = "ordlctl" }
}
if (-not $ordlctlCmd) {
  throw "ordlctl binary not found."
}

$listener = Get-NetTCPConnection -State Listen -LocalPort 18789 -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
  Write-Host "ordlctl gateway appears to be running (port 18789 listening by PID $($listener.OwningProcess))."
  exit 0
}

$already = Get-CimInstance Win32_Process |
  Where-Object {
    $_.Name -match "ordlctl|ordlctl-gateway|node" -and
    $_.CommandLine -and
    ($_.CommandLine -match "ordlctl-gateway" -or $_.CommandLine -match "ordlctl.*gateway\\s+run")
  } | Select-Object -First 1

if ($already) {
  Write-Host "ordlctl gateway already running process detected (PID $($already.ProcessId))."
  exit 0
}

Start-Process -FilePath "cmd.exe" `
  -ArgumentList @("/c", "$ordlctlCmd gateway run --bind $Bind") `
  -WorkingDirectory $stateDir `
  -WindowStyle Hidden `
  -RedirectStandardOutput $logFile `
  -RedirectStandardError $errFile

Write-Host "ordlctl gateway start command submitted."
