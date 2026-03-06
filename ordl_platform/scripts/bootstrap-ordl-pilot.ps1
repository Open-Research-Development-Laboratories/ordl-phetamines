param(
  [string]$ApiBase = "http://127.0.0.1:8891/v1"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function New-AccessToken {
  param(
    [string]$ApiBaseUrl,
    [string]$TenantName,
    [string]$Email,
    [string]$DisplayName,
    [string[]]$Roles,
    [string]$ClearanceTier = "restricted"
  )
  $payload = @{
    tenant_name = $TenantName
    email = $Email
    display_name = $DisplayName
    roles = $Roles
    clearance_tier = $ClearanceTier
    compartments = @("alpha", "ops")
  } | ConvertTo-Json -Depth 6
  return Invoke-RestMethod -Method Post -Uri "$ApiBaseUrl/auth/token" -ContentType "application/json" -Body $payload
}

function Get-Me {
  param([string]$ApiBaseUrl, [string]$Token)
  $headers = @{ Authorization = "Bearer $Token" }
  return Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/auth/me" -Headers $headers
}

function Find-ByName {
  param([object[]]$Items, [string]$Name)
  foreach ($item in $Items) {
    if ($item.name -eq $Name) { return $item }
  }
  return $null
}

Write-Host "== ORDL Pilot Bootstrap =="
Write-Host "API Base: $ApiBase"

$aaron = New-AccessToken -ApiBaseUrl $ApiBase -TenantName "Open Research and Development Laboratories (ORDL)" -Email "aferguson@ordl.org" -DisplayName "Aaron Ferguson" -Roles @("officer","board_member")
$dustin = New-AccessToken -ApiBaseUrl $ApiBase -TenantName "Open Research and Development Laboratories (ORDL)" -Email "dstroup@ordl.org" -DisplayName "Dustin Stroup" -Roles @("engineer","operator")

$aaronToken = $aaron.access_token
$dustinToken = $dustin.access_token
if (-not $aaronToken -or -not $dustinToken) {
  throw "Failed to issue pilot bootstrap tokens."
}

$aaronMe = Get-Me -ApiBaseUrl $ApiBase -Token $aaronToken
$dustinMe = Get-Me -ApiBaseUrl $ApiBase -Token $dustinToken

$headersAaron = @{
  Authorization = "Bearer $aaronToken"
  "Content-Type" = "application/json"
}

$orgs = Invoke-RestMethod -Method Get -Uri "$ApiBase/orgs" -Headers $headersAaron
$org = Find-ByName -Items $orgs -Name "Open Research and Development Laboratories (ORDL)"
if (-not $org) {
  $orgPayload = @{
    tenant_id = $aaronMe.tenant_id
    name = "Open Research and Development Laboratories (ORDL)"
  } | ConvertTo-Json -Depth 4
  $org = Invoke-RestMethod -Method Post -Uri "$ApiBase/orgs" -Headers $headersAaron -Body $orgPayload
}

$teams = Invoke-RestMethod -Method Get -Uri "$ApiBase/teams?org_id=$($org.id)" -Headers $headersAaron
$team = Find-ByName -Items $teams -Name "Platform"
if (-not $team) {
  $teamPayload = @{ org_id = $org.id; name = "Platform" } | ConvertTo-Json -Depth 4
  $team = Invoke-RestMethod -Method Post -Uri "$ApiBase/teams" -Headers $headersAaron -Body $teamPayload
}

$projects = Invoke-RestMethod -Method Get -Uri "$ApiBase/projects?team_id=$($team.id)" -Headers $headersAaron
$project = $null
foreach ($p in $projects) {
  if ($p.code -eq "ORDL-CORE") { $project = $p; break }
}
if (-not $project) {
  $projectPayload = @{
    team_id = $team.id
    code = "ORDL-CORE"
    name = "ORDL Fleet Platform"
    ingress_mode = "zero_trust"
    visibility_mode = "scoped"
  } | ConvertTo-Json -Depth 4
  $project = Invoke-RestMethod -Method Post -Uri "$ApiBase/projects" -Headers $headersAaron -Body $projectPayload
}

$seats = Invoke-RestMethod -Method Get -Uri "$ApiBase/seats?project_id=$($project.id)" -Headers $headersAaron
$dustinSeat = $null
foreach ($seat in $seats) {
  if ($seat.user_id -eq $dustinMe.user_id) { $dustinSeat = $seat; break }
}

if (-not $dustinSeat) {
  $seatPayload = @{
    project_id = $project.id
    user_id = $dustinMe.user_id
    role = "operator"
    rank = "member"
    position = "debugger_tester"
    group_name = "quality"
    clearance_tier = "restricted"
    compartments = @("alpha", "ops")
    status = "active"
  } | ConvertTo-Json -Depth 6
  $dustinSeat = Invoke-RestMethod -Method Post -Uri "$ApiBase/seats" -Headers $headersAaron -Body $seatPayload
}

Write-Host "Pilot bootstrap complete."
@{
  tenant_id = $aaronMe.tenant_id
  org_id = $org.id
  team_id = $team.id
  project_id = $project.id
  users = @(
    @{
      email = "aferguson@ordl.org"
      user_id = $aaronMe.user_id
      roles = $aaronMe.roles
    },
    @{
      email = "dstroup@ordl.org"
      user_id = $dustinMe.user_id
      roles = $dustinMe.roles
      seat_id = $dustinSeat.id
    }
  )
} | ConvertTo-Json -Depth 8
