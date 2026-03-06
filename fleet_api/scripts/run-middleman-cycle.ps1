param(
  [string[]]$Roles = @("worker-build-laptop", "worker-batch-server"),
  [string]$HandoffGlob = "/development/crew-handoff/*.md",
  [int]$MaxChars = 2500,
  [string]$SshPassword = "",
  [string]$Feedback = "",
  [switch]$NoPause
)

$ErrorActionPreference = "Stop"

$repoRoot = "C:\Users\Winsock\Documents\GitHub\ordl-phetamines"
$stageScript = Join-Path $repoRoot "fleet_api\scripts\stage-worker-reports-to-openclaw-chat.ps1"
$reworkScript = Join-Path $repoRoot "fleet_api\scripts\rework-worker-reports.ps1"

if (-not (Test-Path $stageScript)) {
  throw "Missing script: $stageScript"
}
if (-not (Test-Path $reworkScript)) {
  throw "Missing script: $reworkScript"
}

Write-Host ""
Write-Host "=== Fleet Middle-Man Cycle ==="
Write-Host "Step 1/3: Stage latest worker reports into OpenClaw chat..."
Write-Host ""

$stageParams = @{
  Roles = $Roles
  HandoffGlob = $HandoffGlob
  MaxChars = $MaxChars
}
if ($SshPassword) {
  $stageParams["SshPassword"] = $SshPassword
}
& $stageScript @stageParams
if ($LASTEXITCODE -ne 0) {
  throw "Staging worker reports failed."
}

Write-Host ""
Write-Host "Step 2/3: Middle-man review checkpoint."
Write-Host "Review/edit in OpenClaw chat."
Write-Host ""
Write-Host "Session status command:"
Write-Host "  openclaw sessions --json"
Write-Host ""

if ($Feedback) {
  Write-Host "Initial feedback provided via -Feedback; running one rework loop..."
  $reworkParams = @{
    Roles = $Roles
    HandoffGlob = $HandoffGlob
    Feedback = $Feedback
  }
  if ($SshPassword) {
    $reworkParams["SshPassword"] = $SshPassword
  }
  & $reworkScript @reworkParams
  if ($LASTEXITCODE -ne 0) {
    throw "Worker rework failed."
  }
  Write-Host ""
  Write-Host "Step 3/3: Restaging revised reports into OpenClaw chat..."
  & $stageScript @stageParams
  if ($LASTEXITCODE -ne 0) {
    throw "Restaging revised reports failed."
  }
}

if ($NoPause) {
  Write-Host "NoPause set: stopping after current cycle."
  Write-Host "Middle-man cycle complete."
  exit 0
}

while ($true) {
  Write-Host ""
  Write-Host "Loop options:"
  Write-Host "  [R] Rework and restage"
  Write-Host "  [D] Done (exit pipeline)"
  $choice = (Read-Host "Choose R or D").Trim().ToLowerInvariant()
  if ($choice -eq "d" -or $choice -eq "done") {
    break
  }
  if ($choice -ne "r" -and $choice -ne "rework") {
    Write-Warning "Invalid option. Enter R or D."
    continue
  }

  $loopFeedback = Read-Host "Enter middle-man feedback for worker rework"
  if (-not $loopFeedback) {
    Write-Warning "Feedback empty; skipping rework."
    continue
  }

  $reworkParams = @{
    Roles = $Roles
    HandoffGlob = $HandoffGlob
    Feedback = $loopFeedback
  }
  if ($SshPassword) {
    $reworkParams["SshPassword"] = $SshPassword
  }

  & $reworkScript @reworkParams
  if ($LASTEXITCODE -ne 0) {
    throw "Worker rework failed."
  }

  Write-Host ""
  Write-Host "Step 3/3: Restaging revised reports into OpenClaw chat..."
  & $stageScript @stageParams
  if ($LASTEXITCODE -ne 0) {
    throw "Restaging revised reports failed."
  }

  Write-Host ""
  Write-Host "Rework submitted and restaged. Review in OpenClaw chat, then choose next loop action."
}

Write-Host ""
Write-Host "Middle-man cycle complete."
