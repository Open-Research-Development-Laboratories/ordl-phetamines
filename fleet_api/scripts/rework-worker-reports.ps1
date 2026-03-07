param(
  [string[]]$Roles = @(),
  [string]$HandoffGlob = "/development/crew-handoff/*.md",
  [string]$Feedback = "",
  [string]$Thinking = "low",
  [string]$SshPassword = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$scriptPath = Join-Path $repoRoot "fleet_api\scripts\rework-worker-reports.py"

if (-not (Test-Path $scriptPath)) {
  throw "Script not found: $scriptPath"
}

if (-not $Feedback) {
  $Feedback = Read-Host "Enter middle-man feedback for worker rework"
}
if (-not $Feedback) {
  throw "Feedback is required."
}

if ($SshPassword) {
  $env:FLEET_SSH_PASSWORD = $SshPassword.Trim()
}

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
  $env:FLEET_SSH_PASSWORD = $plain.Trim()
}

$args = @(
  $scriptPath,
  "--feedback", $Feedback,
  "--handoff-glob", $HandoffGlob,
  "--thinking", $Thinking,
  "--quiet"
)
if ($Roles -and $Roles.Count -gt 0) {
  $args += "--roles"
  $args += $Roles
}

& python -u @args
exit $LASTEXITCODE
