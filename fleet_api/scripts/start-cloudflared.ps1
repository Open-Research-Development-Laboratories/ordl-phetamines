param(
  [string]$RepoRoot = "",
  [string]$TunnelToken = $env:CLOUDFLARE_TUNNEL_TOKEN,
  [string]$LocalUrl = "http://127.0.0.1:8890",
  [string]$CloudflaredPath = ""
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
  $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

$stateDir = Join-Path $RepoRoot "fleet_api\state"
$logFile = Join-Path $stateDir "cloudflared.log"
$errFile = Join-Path $stateDir "cloudflared.err.log"
New-Item -ItemType Directory -Force -Path $stateDir | Out-Null

$cloudflared = $null
if ($CloudflaredPath -and (Test-Path $CloudflaredPath)) {
  $cloudflared = $CloudflaredPath
}

if (-not $cloudflared) {
  $cmd = Get-Command cloudflared -ErrorAction SilentlyContinue
  if ($cmd) { $cloudflared = $cmd.Source }
}

if (-not $cloudflared) {
  $cmdExe = Get-Command cloudflared.exe -ErrorAction SilentlyContinue
  if ($cmdExe) { $cloudflared = $cmdExe.Source }
}

if (-not $cloudflared) {
  $candidates = @(
    "$env:ProgramFiles\cloudflared\cloudflared.exe",
    "${env:ProgramFiles(x86)}\cloudflared\cloudflared.exe",
    "$env:LOCALAPPDATA\Programs\cloudflared\cloudflared.exe",
    "$env:USERPROFILE\.cloudflared\cloudflared.exe"
  ) | Where-Object { $_ -and $_.Trim() -ne "" }

  foreach ($candidate in $candidates) {
    if (Test-Path $candidate) {
      $cloudflared = $candidate
      break
    }
  }
}

if (-not $cloudflared) {
  throw "cloudflared not found. Install with: winget install --id Cloudflare.cloudflared -e"
}

$already = Get-CimInstance Win32_Process |
  Where-Object {
    $_.Name -match "cloudflared" -and
    $_.CommandLine -and
    $_.CommandLine -match "127.0.0.1:8890|tunnel run"
  }
if ($already) {
  Write-Host "cloudflared already running."
  exit 0
}

if ($TunnelToken) {
  $args = @("tunnel", "run", "--token", $TunnelToken)
  Write-Host "Starting cloudflared with named tunnel token."
}
else {
  $args = @("tunnel", "--no-autoupdate", "--url", $LocalUrl)
  Write-Host "Starting cloudflared quick tunnel."
}

Start-Process -FilePath $cloudflared `
  -ArgumentList $args `
  -WorkingDirectory $stateDir `
  -WindowStyle Hidden `
  -RedirectStandardOutput $logFile `
  -RedirectStandardError $errFile

Write-Host "cloudflared start command submitted."
