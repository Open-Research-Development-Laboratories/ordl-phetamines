param(
  [string]$LanIp
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command openclaw -ErrorAction SilentlyContinue)) {
  throw "openclaw not found in PATH"
}

function Get-DefaultLanIp {
  $ips = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object {
      $_.IPAddress -notmatch '^127\.' -and
      $_.IPAddress -notmatch '^169\.254\.' -and
      $_.PrefixOrigin -in @('Dhcp', 'Manual', 'RouterAdvertisement')
    } |
    Select-Object -ExpandProperty IPAddress
  return $ips | Select-Object -First 1
}

if (-not $LanIp -or [string]::IsNullOrWhiteSpace($LanIp)) {
  $LanIp = Get-DefaultLanIp
}
$LanIp = (($LanIp | Out-String).Trim())

$cfgPath = Join-Path $HOME ".openclaw\openclaw.json"
$cfg = Get-Content -Raw $cfgPath | ConvertFrom-Json

if (-not $cfg.gateway) { $cfg | Add-Member -NotePropertyName gateway -NotePropertyValue ([pscustomobject]@{}) }
$cfg.gateway.mode = "local"
$cfg.gateway.bind = "lan"

if (-not $cfg.gateway.remote) { $cfg.gateway | Add-Member -NotePropertyName remote -NotePropertyValue ([pscustomobject]@{}) }
$cfg.gateway.remote.url = "ws://127.0.0.1:18789"

if (-not $cfg.gateway.auth) { $cfg.gateway | Add-Member -NotePropertyName auth -NotePropertyValue ([pscustomobject]@{}) }
if (-not $cfg.gateway.auth.rateLimit) { $cfg.gateway.auth | Add-Member -NotePropertyName rateLimit -NotePropertyValue ([pscustomobject]@{}) }
$cfg.gateway.auth.rateLimit.maxAttempts = 10
$cfg.gateway.auth.rateLimit.windowMs = 60000
$cfg.gateway.auth.rateLimit.lockoutMs = 300000

if (-not $cfg.gateway.controlUi) { $cfg.gateway | Add-Member -NotePropertyName controlUi -NotePropertyValue ([pscustomobject]@{}) }
if (-not $cfg.gateway.controlUi.allowedOrigins) {
  $cfg.gateway.controlUi | Add-Member -NotePropertyName allowedOrigins -NotePropertyValue @("http://127.0.0.1:18789")
}

$origins = @($cfg.gateway.controlUi.allowedOrigins)
if ($origins -notcontains "http://127.0.0.1:18789") { $origins += "http://127.0.0.1:18789" }
if ($LanIp -match '^\d{1,3}(\.\d{1,3}){3}$') {
  $lanOrigin = "http://${LanIp}:18789"
  if ($origins -notcontains $lanOrigin) { $origins += $lanOrigin }
}
$cfg.gateway.controlUi.allowedOrigins = $origins

$cfg | ConvertTo-Json -Depth 100 | Set-Content $cfgPath -NoNewline

Write-Host "[hub-win] gateway.mode=local, bind=lan, remote.url=ws://127.0.0.1:18789"
if ($LanIp -match '^\d{1,3}(\.\d{1,3}){3}$') {
  Write-Host "[hub-win] allowed origin added: http://${LanIp}:18789"
}

Write-Host "[hub-win] token:"
openclaw config get gateway.auth.token

Write-Host "[hub-win] run:"
Write-Host "openclaw gateway run --bind lan"
