param(
  [string[]]$Roles = @(),
  [string]$HandoffGlob = "/development/crew-handoff/*.md",
  [string]$SessionId = "",
  [int]$MaxChars = 3200
)

$ErrorActionPreference = "Stop"

$repoRoot = "C:\Users\Winsock\Documents\GitHub\ordl-phetamines"
$scriptPath = Join-Path $repoRoot "fleet_api\scripts\stage-worker-reports-to-openclaw-chat.py"

if (-not (Test-Path $scriptPath)) {
  throw "Script not found: $scriptPath"
}

Write-Host "Starting worker report staging into OpenClaw chat..."

if (-not $env:FLEET_SSH_PASSWORD) {
  Write-Host "FLEET_SSH_PASSWORD is not set; waiting for secure input..."
  $secure = Read-Host "FLEET_SSH_PASSWORD" -AsSecureString
  $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
  try {
    $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
  }
  finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
  }
  $env:FLEET_SSH_PASSWORD = $plain
}

$args = @($scriptPath, "--handoff-glob", $HandoffGlob, "--max-chars", "$MaxChars")
if ($Roles -and $Roles.Count -gt 0) {
  $args += "--roles"
  $args += $Roles
}
if ($SessionId) {
  $args += "--session-id"
  $args += $SessionId
}

python -u @args
