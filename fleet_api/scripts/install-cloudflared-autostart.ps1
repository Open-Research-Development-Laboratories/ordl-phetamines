param(
  [string]$RepoRoot = "C:\Users\Winsock\Documents\GitHub\ordl-phetamines",
  [string]$TaskName = "FleetTunnel-Autostart"
)

$ErrorActionPreference = "Stop"

$startScript = Join-Path $RepoRoot "fleet_api\scripts\start-cloudflared.ps1"
if (!(Test-Path $startScript)) {
  throw "Missing start script: $startScript"
}

$arg = "-NoProfile -ExecutionPolicy Bypass -File `"$startScript`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arg
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew

try {
  $triggerLogon = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
  $triggerStartup = New-ScheduledTaskTrigger -AtStartup
  Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger @($triggerLogon, $triggerStartup) -Settings $settings -Description "Auto-start Cloudflare tunnel for Fleet API" -Force | Out-Null
  Write-Host "Registered $TaskName (startup + logon)."
}
catch {
  Write-Host "Startup trigger registration failed. Falling back to logon-only trigger."
  $triggerLogon = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
  Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $triggerLogon -Settings $settings -Description "Auto-start Cloudflare tunnel for Fleet API at logon" -Force | Out-Null
}

Start-ScheduledTask -TaskName $TaskName
Write-Host "$TaskName started."

if (-not $env:CLOUDFLARE_TUNNEL_TOKEN) {
  Write-Host "CLOUDFLARE_TUNNEL_TOKEN not set; script started cloudflared in quick tunnel mode."
}

