param(
  [string[]]$Roles = @(),
  [switch]$RotateIdentity
)

$ErrorActionPreference = "Stop"

$repoRoot = "C:\Users\Winsock\Documents\GitHub\ordl-phetamines"
$scriptPath = Join-Path $repoRoot "fleet_api\scripts\resync-fleet-tokens.py"

if (-not (Test-Path $scriptPath)) {
  throw "Script not found: $scriptPath"
}

Write-Host "Starting fleet token resync..."

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

$args = @($scriptPath)
if ($Roles -and $Roles.Count -gt 0) {
  $args += "--roles"
  $args += $Roles
}
if ($RotateIdentity) {
  $args += "--rotate-identity"
}

Write-Host "Running token sync script..."
python -u @args
