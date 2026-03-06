param(
  [switch]$StartStack
)

Write-Host '== ORDL Session Bootstrap ==' -ForegroundColor Cyan

$cfg = "$env:USERPROFILE\.codex\config.toml"
if (Test-Path $cfg) {
  Write-Host "Codex config found: $cfg"
} else {
  Write-Warning 'Codex config.toml not found'
}

Write-Host 'MCP note: verify servers from Codex UI after startup (context7, playwright, server_fetch, antiforge).'
Write-Host 'Memory note: load memory/YYYY-MM-DD.md and AGENTS.md (canonical instructions) before execution.'

Write-Host ''
Write-Host 'Running MCP probe...'
$probeScript = Join-Path $PSScriptRoot 'refresh-codex-mcp.ps1'
powershell -ExecutionPolicy Bypass -File $probeScript

if ($StartStack) {
  Write-Host 'Starting ORDL clean-room stack via podman-compose...'
  Push-Location "ordl_platform/infra"
  podman-compose -f podman-compose.yml up --build
  Pop-Location
}
