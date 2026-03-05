param(
  [string]$RepoRoot = "C:\Users\Winsock\Documents\GitHub\ordl-phetamines",
  [string]$HubTaskName = "OpenClawHub-Autostart",
  [string]$ApiTaskName = "FleetAPI-Autostart",
  [string]$TunnelTaskName = "FleetTunnel-Autostart"
)

$ErrorActionPreference = "Stop"

$hubInstaller = Join-Path $RepoRoot "fleet_api\scripts\install-openclaw-hub-autostart.ps1"
$apiInstaller = Join-Path $RepoRoot "fleet_api\scripts\install-desktop-autostart.ps1"
$tunnelInstaller = Join-Path $RepoRoot "fleet_api\scripts\install-cloudflared-autostart.ps1"

if (!(Test-Path $hubInstaller)) {
  throw "Missing hub installer: $hubInstaller"
}
if (!(Test-Path $apiInstaller)) {
  throw "Missing API installer: $apiInstaller"
}
if (!(Test-Path $tunnelInstaller)) {
  throw "Missing tunnel installer: $tunnelInstaller"
}

powershell -NoProfile -ExecutionPolicy Bypass -File $hubInstaller -RepoRoot $RepoRoot -TaskName $HubTaskName
powershell -NoProfile -ExecutionPolicy Bypass -File $apiInstaller -RepoRoot $RepoRoot -TaskName $ApiTaskName
powershell -NoProfile -ExecutionPolicy Bypass -File $tunnelInstaller -RepoRoot $RepoRoot -TaskName $TunnelTaskName

Write-Host "Desktop autostart configured:"
Write-Host "- $HubTaskName"
Write-Host "- $ApiTaskName"
Write-Host "- $TunnelTaskName"
