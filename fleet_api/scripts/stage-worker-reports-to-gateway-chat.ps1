param(
  [string[]]$Roles = @(),
  [string]$HandoffGlob = "/development/crew-handoff/*.md",
  [string]$SessionId = "",
  [int]$MaxChars = 3200,
  [string]$SshPassword = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = "C:\Users\Winsock\Documents\GitHub\ordl-phetamines"
$scriptPath = Join-Path $repoRoot "fleet_api\scripts\stage-worker-reports-to-gateway-chat.py"

if (-not (Test-Path $scriptPath)) {
  throw "Script not found: $scriptPath"
}

Write-Host "Starting worker report staging into ordlctl chat..."

if ($SshPassword) {
  $env:FLEET_SSH_PASSWORD = $SshPassword.Trim()
}

$args = @($scriptPath, "--handoff-glob", $HandoffGlob, "--max-chars", "$MaxChars", "--quiet")
if ($Roles -and $Roles.Count -gt 0) {
  $args += "--roles"
  $args += $Roles
}
if ($SessionId) {
  $args += "--session-id"
  $args += $SessionId
}

$maxAttempts = 2
for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
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

  $tmpOut = New-TemporaryFile
  $tmpErr = New-TemporaryFile
  try {
    $prevErrAction = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & python -u @args 1> $tmpOut 2> $tmpErr
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = $prevErrAction
    $stdoutText = if (Test-Path $tmpOut) { Get-Content $tmpOut -Raw } else { "" }
    $stderrText = if (Test-Path $tmpErr) { Get-Content $tmpErr -Raw } else { "" }

    if ($stdoutText) {
      $stdoutText.TrimEnd("`r", "`n").Split("`n") | ForEach-Object { Write-Host $_ }
    }
    if ($stderrText) {
      $stderrText.TrimEnd("`r", "`n").Split("`n") | ForEach-Object { Write-Host $_ }
    }
  }
  finally {
    $ErrorActionPreference = "Stop"
    Remove-Item $tmpOut -Force -ErrorAction SilentlyContinue
    Remove-Item $tmpErr -Force -ErrorAction SilentlyContinue
  }

  if ($exitCode -eq 0) {
    exit 0
  }

  $text = "$stdoutText`n$stderrText"
  if (($attempt -lt $maxAttempts) -and ($text -match "Authentication failed")) {
    Write-Warning "SSH authentication failed. Re-enter worker SSH password and retrying once..."
    Remove-Item Env:FLEET_SSH_PASSWORD -ErrorAction SilentlyContinue
    continue
  }

  exit $exitCode
}
