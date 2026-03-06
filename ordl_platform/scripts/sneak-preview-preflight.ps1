param(
  [ValidateSet("auto", "container", "local")]
  [string]$PreviewMode = "auto",
  [string]$EnvFile = "",
  [switch]$InitEnvFile,
  [switch]$SkipReleaseGate,
  [switch]$UseLocalProfiles,
  [string]$ApiBase = "http://127.0.0.1:8891/v1"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
$infraDir = Join-Path $repoRoot "ordl_platform\\infra"
$composeFile = Join-Path $infraDir "podman-compose.prod.yml"
$exampleEnv = Join-Path $infraDir ".env.prod.example"
$releaseGateScript = Join-Path $repoRoot "ordl_platform\\scripts\\release-gate.ps1"
$startDevScript = Join-Path $repoRoot "ordl_platform\\scripts\\start-dev.ps1"

if ([string]::IsNullOrWhiteSpace($EnvFile)) {
  $EnvFile = Join-Path $infraDir ".env.prod"
}

function Write-Section {
  param([string]$Name)
  Write-Host ""
  Write-Host "== $Name =="
}

function Read-EnvFile {
  param([string]$Path)
  $dict = @{}
  foreach ($line in Get-Content $Path) {
    $trimmed = $line.Trim()
    if (-not $trimmed -or $trimmed.StartsWith("#")) { continue }
    $eq = $trimmed.IndexOf("=")
    if ($eq -lt 1) { continue }
    $key = $trimmed.Substring(0, $eq).Trim()
    $value = $trimmed.Substring($eq + 1).Trim()
    $dict[$key] = $value
  }
  return $dict
}

function Is-Placeholder {
  param([string]$Value)
  if ([string]::IsNullOrWhiteSpace($Value)) { return $true }
  $lower = $Value.ToLowerInvariant()
  if ($lower.Contains("change-me")) { return $true }
  if ($lower.Contains("replace-with")) { return $true }
  if ($lower.Contains("example.com")) { return $true }
  return $false
}

function Require-Keys {
  param(
    [hashtable]$Data,
    [string[]]$Keys,
    [string]$Context
  )
  $missing = @()
  foreach ($k in $Keys) {
    if (-not $Data.ContainsKey($k) -or [string]::IsNullOrWhiteSpace([string]$Data[$k])) {
      $missing += $k
    }
  }
  if ($missing.Count -gt 0) {
    throw "$Context missing required keys: $($missing -join ', ')"
  }
}

function Resolve-ContainerRuntime {
  $result = @{
    runtime = ""
    composeCmd = ""
  }

  $podmanCmd = Get-Command podman -ErrorAction SilentlyContinue
  $podmanComposeCmd = Get-Command podman-compose -ErrorAction SilentlyContinue
  if ($podmanCmd -and $podmanComposeCmd) {
    $result.runtime = "podman"
    $result.composeCmd = "podman-compose"
    return $result
  }

  $dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
  if ($dockerCmd) {
    try {
      & docker compose version | Out-Null
      $result.runtime = "docker"
      $result.composeCmd = "docker compose"
      return $result
    } catch {
      # no-op, fallback to local mode
    }
  }
  return $result
}

Write-Section "ORDL Sneak Preview Preflight"
Write-Host "Repo: $repoRoot"
Write-Host "Requested mode: $PreviewMode"

if (-not (Test-Path $releaseGateScript)) {
  throw "Release gate script not found: $releaseGateScript"
}

$runtime = Resolve-ContainerRuntime
$actualMode = $PreviewMode
if ($PreviewMode -eq "auto") {
  $actualMode = if ([string]::IsNullOrWhiteSpace($runtime.composeCmd)) { "local" } else { "container" }
}

if ($actualMode -eq "container" -and [string]::IsNullOrWhiteSpace($runtime.composeCmd)) {
  throw "Container mode requested but no supported runtime found (podman+podman-compose or docker compose)."
}

Write-Host "Effective mode: $actualMode"

Write-Section "Tooling"
python --version
npm --version
if ($actualMode -eq "container") {
  if ($runtime.runtime -eq "podman") {
    podman --version
    podman-compose --version
  } elseif ($runtime.runtime -eq "docker") {
    docker --version
    docker compose version
  }
} else {
  Write-Host "Container runtime not required for local preview mode."
}

if ($actualMode -eq "container") {
  if (-not (Test-Path $composeFile)) {
    throw "Compose file not found: $composeFile"
  }

  if (-not (Test-Path $EnvFile)) {
    if ($InitEnvFile) {
      if (-not (Test-Path $exampleEnv)) {
        throw "Env template not found: $exampleEnv"
      }
      Copy-Item $exampleEnv $EnvFile -Force
      Write-Host "Created env file from template: $EnvFile"
      Write-Host "Fill required values and rerun."
      exit 2
    }
    throw "Missing env file: $EnvFile (rerun with -InitEnvFile to create template)"
  }

  Write-Host "Env file: $EnvFile"
  $envMap = Read-EnvFile -Path $EnvFile

  Write-Section "Environment Validation"
  Require-Keys -Data $envMap -Context "Base env" -Keys @(
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "ORDL_DATABASE_URL",
    "ORDL_POLICY_SECRET",
    "ORDL_AUTH_SECRET",
    "ORDL_EXTENSION_SIGNING_SECRET",
    "ORDL_SECRET_BACKEND",
    "ORDL_OIDC_ENABLED",
    "ORDL_OIDC_REQUIRED",
    "ORDL_ALLOW_LOCAL_TOKEN_ISSUER",
    "VITE_ORDL_API_BASE"
  )

  foreach ($secretKey in @("ORDL_POLICY_SECRET", "ORDL_AUTH_SECRET", "ORDL_EXTENSION_SIGNING_SECRET")) {
    if (Is-Placeholder -Value ([string]$envMap[$secretKey])) {
      throw "Weak/placeholder value for $secretKey"
    }
  }

  $secretBackend = [string]$envMap["ORDL_SECRET_BACKEND"]
  if ($secretBackend -eq "vault") {
    if (-not $UseLocalProfiles) {
      Require-Keys -Data $envMap -Context "Vault env" -Keys @("ORDL_VAULT_URL", "ORDL_VAULT_KV_MOUNT", "ORDL_VAULT_KV_PATH")
      if (Is-Placeholder -Value ([string]$envMap["ORDL_VAULT_URL"])) {
        throw "ORDL_VAULT_URL is placeholder"
      }
    } else {
      Require-Keys -Data $envMap -Context "Local vault env" -Keys @("VAULT_DEV_ROOT_TOKEN_ID")
    }
  }

  $oidcEnabled = ([string]$envMap["ORDL_OIDC_ENABLED"]).ToLowerInvariant() -eq "true"
  $oidcRequired = ([string]$envMap["ORDL_OIDC_REQUIRED"]).ToLowerInvariant() -eq "true"
  if ($oidcEnabled -and $oidcRequired -and -not $UseLocalProfiles) {
    Require-Keys -Data $envMap -Context "OIDC env" -Keys @("ORDL_OIDC_ISSUER", "ORDL_OIDC_JWKS_URL", "ORDL_OIDC_AUDIENCE")
    foreach ($k in @("ORDL_OIDC_ISSUER", "ORDL_OIDC_JWKS_URL", "ORDL_OIDC_AUDIENCE")) {
      if (Is-Placeholder -Value ([string]$envMap[$k])) {
        throw "$k is placeholder"
      }
    }
  }

  Write-Host "Env validation passed."

  Write-Section "Compose Validation"
  Push-Location $infraDir
  try {
    foreach ($k in $envMap.Keys) {
      Set-Item -Path "Env:$k" -Value ([string]$envMap[$k]) | Out-Null
    }
    if ($runtime.runtime -eq "podman") {
      podman-compose -f $composeFile config | Out-Null
    } else {
      docker compose -f $composeFile config | Out-Null
    }
    Write-Host "Compose config validation passed."
  } finally {
    Pop-Location
  }
}

if (-not $SkipReleaseGate) {
  Write-Section "Release Gate"
  powershell -ExecutionPolicy Bypass -File $releaseGateScript
}

Write-Section "Fleet Pairing"
$deviceJson = openclaw devices list --json | ConvertFrom-Json
$pendingCount = @($deviceJson.pending).Count
Write-Host "Pending pairings: $pendingCount"
if ($pendingCount -gt 0) {
  throw "Fleet has pending pairings. Resolve before preview launch."
}

Write-Section "Preview Commands"
if ($actualMode -eq "container") {
  $profiles = ""
  if ($UseLocalProfiles) {
    $profiles = "--profile local-vault --profile local-idp "
  }
  Write-Host "From: $infraDir"
  if ($runtime.runtime -eq "podman") {
    Write-Host "Launch stack:"
    Write-Host "  podman-compose -f `"$composeFile`" $profiles up --build -d"
  } else {
    Write-Host "Launch stack:"
    Write-Host "  docker compose -f `"$composeFile`" $profiles up --build -d"
  }
} else {
  Write-Host "Local runtime preview commands:"
  Write-Host "  powershell -ExecutionPolicy Bypass -File `"$startDevScript`" -Api -Ui"
}
Write-Host "API health:"
Write-Host "  curl $ApiBase/../health"
Write-Host "Bootstrap pilot:"
Write-Host "  powershell -ExecutionPolicy Bypass -File `"$repoRoot\\ordl_platform\\scripts\\bootstrap-ordl-pilot.ps1`" -ApiBase $ApiBase"
Write-Host "Bootstrap adopted standards:"
Write-Host "  powershell -ExecutionPolicy Bypass -File `"$repoRoot\\ordl_platform\\scripts\\bootstrap-adopted-standards.ps1`" -ApiBase $ApiBase"

Write-Section "Preflight Result"
Write-Host "Sneak preview preflight passed."
