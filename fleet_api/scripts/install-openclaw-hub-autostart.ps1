param(
  [string]$RepoRoot = "C:\Users\Winsock\Documents\GitHub\ordl-phetamines",
  [string]$TaskName = "OpenClawHub-Autostart"
)

$ErrorActionPreference = "Stop"

$startScript = Join-Path $RepoRoot "fleet_api\scripts\start-openclaw-hub.ps1"
if (!(Test-Path $startScript)) {
  throw "Missing start script: $startScript"
}

$arg = "-NoProfile -ExecutionPolicy Bypass -File `"$startScript`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arg
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew

try {
  $triggerLogon = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
  $triggerStartup = New-ScheduledTaskTrigger -AtStartup
  Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger @($triggerLogon, $triggerStartup) -Settings $settings -Description "Auto-start OpenClaw gateway hub" -Force | Out-Null
  Write-Host "Registered $TaskName (startup + logon)."
}
catch {
  Write-Host "Startup trigger registration failed. Falling back to logon-only trigger."
  $triggerLogon = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
  Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $triggerLogon -Settings $settings -Description "Auto-start OpenClaw gateway hub at logon" -Force | Out-Null
}

Start-ScheduledTask -TaskName $TaskName
Write-Host "$TaskName started."

