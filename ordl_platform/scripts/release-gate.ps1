param(
  [switch]$SkipFrontendBuild,
  [switch]$SkipFleetTests,
  [switch]$SkipOpenAIStandards,
  [string]$FlaskRevisionPath = "",
  [string]$Rev8ContractMatrixPath = "",
  [string]$OpenAIReportPath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path

Write-Host "== ORDL Release Gate =="
Write-Host "Repo: $repoRoot"

function Invoke-External {
  param(
    [string]$Command,
    [string[]]$CommandArgs
  )
  & $Command @CommandArgs
  if ($LASTEXITCODE -ne 0) {
    throw "External command failed ($LASTEXITCODE): $Command $($CommandArgs -join ' ')"
  }
}

function Invoke-Step {
  param(
    [string]$Name,
    [scriptblock]$Script
  )
  Write-Host ""
  Write-Host ">> $Name"
  & $Script
}

Invoke-Step -Name "Backend tests (ordl_platform/backend)" -Script {
  Push-Location (Join-Path $repoRoot "ordl_platform\\backend")
  try {
    Invoke-External -Command "python" -CommandArgs @("-m", "pytest", "-q")
  } finally {
    Pop-Location
  }
}

Invoke-Step -Name "Generate /v1 API contract artifacts" -Script {
  Push-Location (Join-Path $repoRoot "ordl_platform")
  try {
    Invoke-External -Command "python" -CommandArgs @("scripts\\generate-v1-contract.py")
  } finally {
    Pop-Location
  }
}

if ($OpenAIReportPath) {
  Invoke-Step -Name "Build OpenAI alignment manifest/backlog" -Script {
    Push-Location (Join-Path $repoRoot "ordl_platform")
    try {
      $resolvedReport = (Resolve-Path $OpenAIReportPath).Path
      Invoke-External -Command "python" -CommandArgs @("scripts\\build-openai-alignment-manifest.py", "--input", $resolvedReport)
    } finally {
      Pop-Location
    }
  }
}

if (-not $SkipOpenAIStandards) {
  Invoke-Step -Name "Validate OpenAI standards implementation" -Script {
    Push-Location (Join-Path $repoRoot "ordl_platform")
    try {
      $reportPath = Join-Path $repoRoot "ordl_platform\\state\\reports\\openai-standards-validation.json"
      Invoke-External -Command "python" -CommandArgs @("scripts\\validate-openai-standards.py", "--out-json", $reportPath)
    } finally {
      Pop-Location
    }
  }
}

if (-not $SkipFleetTests) {
  Invoke-Step -Name "Fleet API tests (fleet_api/tests)" -Script {
    Push-Location $repoRoot
    try {
      Invoke-External -Command "python" -CommandArgs @("-m", "pytest", "-q", "fleet_api/tests")
    } finally {
      Pop-Location
    }
  }
}

if ($Rev8ContractMatrixPath) {
  Invoke-Step -Name "Revision 8 contract matrix review" -Script {
    Push-Location (Join-Path $repoRoot "ordl_platform")
    try {
      $resolvedMatrix = (Resolve-Path $Rev8ContractMatrixPath).Path
      Invoke-External -Command "python" -CommandArgs @("scripts\\review-revision8-contract.py", "--matrix", $resolvedMatrix)
    } finally {
      Pop-Location
    }
  }
}

if ($FlaskRevisionPath) {
  Invoke-Step -Name "Flask revision audit gate" -Script {
    Push-Location (Join-Path $repoRoot "ordl_platform")
    try {
      $resolved = (Resolve-Path $FlaskRevisionPath).Path
      $reportPath = Join-Path $repoRoot "ordl_platform\\state\\reports\\flask-revision-audit.json"
      Invoke-External -Command "python" -CommandArgs @("scripts\\audit-flask-revision.py", "--revision-root", $resolved, "--out-json", $reportPath)
    } finally {
      Pop-Location
    }
  }
}

if (-not $SkipFrontendBuild) {
  Invoke-Step -Name "Frontend build (ordl_platform/frontend)" -Script {
    Push-Location (Join-Path $repoRoot "ordl_platform\\frontend")
    try {
      Invoke-External -Command "npm" -CommandArgs @("run", "build")
    } finally {
      Pop-Location
    }
  }
}

Write-Host ""
Write-Host "Release gate passed."
