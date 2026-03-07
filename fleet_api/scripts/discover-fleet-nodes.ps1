param(
  [string]$ApiBase = "http://127.0.0.1:8890",
  [string]$ApiKey = $env:FLEET_API_KEY,
  [string[]]$Cidrs = @("198.51.100.0/24"),
  [string[]]$Hosts = @(),
  [int]$MaxHosts = 256,
  [switch]$NoSshProbe,
  [switch]$AutoDeploy,
  [switch]$Async
)

$ErrorActionPreference = "Stop"

if (-not $ApiKey) {
  throw "FLEET_API_KEY is required."
}

$headers = @{ "X-API-Key" = $ApiKey }
$body = @{
  cidrs = $Cidrs
  hosts = $Hosts
  max_hosts = $MaxHosts
  attempt_ssh = -not $NoSshProbe.IsPresent
  auto_deploy = $AutoDeploy.IsPresent
  async = $Async.IsPresent
} | ConvertTo-Json -Depth 8

Write-Host "Starting discovery scan..."
$res = Invoke-RestMethod -Method Post -Uri "$ApiBase/v1/fleet/discovery/scan" -Headers $headers -Body $body -ContentType "application/json"
$res | ConvertTo-Json -Depth 10
