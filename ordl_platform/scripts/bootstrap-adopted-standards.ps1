param(
  [string]$ApiBase = "http://127.0.0.1:8891/v1",
  [string]$TenantName = "ORDL",
  [string]$Email = "officer@ordl.local",
  [string]$DisplayName = "ORDL Officer",
  [switch]$OverwriteExisting
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "== ORDL Adopted Standards Bootstrap =="
Write-Host "API Base: $ApiBase"

$tokenPayload = @{
  tenant_name = $TenantName
  email = $Email
  display_name = $DisplayName
  roles = @("officer")
  clearance_tier = "restricted"
  compartments = @("alpha", "ops")
} | ConvertTo-Json -Depth 6

try {
  $tokenRes = Invoke-RestMethod -Method Post -Uri "$ApiBase/auth/token" -ContentType "application/json" -Body $tokenPayload
} catch {
  throw "Failed to issue bootstrap token from $ApiBase/auth/token. $($_.Exception.Message)"
}

if (-not $tokenRes.access_token) {
  throw "Token response missing access_token."
}

$headers = @{
  "Authorization" = "Bearer $($tokenRes.access_token)"
  "Content-Type" = "application/json"
}

$bootstrapPayload = @{
  overwrite_existing = [bool]$OverwriteExisting
  include_versions = $true
} | ConvertTo-Json -Depth 4

try {
  $bootstrapRes = Invoke-RestMethod -Method Post -Uri "$ApiBase/protocols/bootstrap/adopted" -Headers $headers -Body $bootstrapPayload
} catch {
  throw "Failed to bootstrap adopted standards. $($_.Exception.Message)"
}

Write-Host "Bootstrap complete."
$bootstrapRes | ConvertTo-Json -Depth 8
