Write-Host '== MCP Refresh Check ==' -ForegroundColor Cyan

$config = "$env:USERPROFILE\.codex\config.toml"
if (Test-Path $config) {
  Write-Host "Config: $config"
  Get-Content $config | Select-String -Pattern '^\[mcp_servers\.|^enabled\s*=\s*true|^command\s*=|^args\s*=' | ForEach-Object { $_.Line }
} else {
  Write-Warning 'No Codex config found.'
}

Write-Host ''
Write-Host 'Binary checks:'
node --version
npx --version
uvx --version

function Invoke-Probe {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Name,
    [Parameter(Mandatory = $true)]
    [string]$Command,
    [int]$TimeoutSeconds = 20
  )

  $proc = Start-Process -FilePath 'cmd.exe' -ArgumentList "/c $Command >nul 2>&1" -PassThru -WindowStyle Hidden
  if (-not $proc.WaitForExit($TimeoutSeconds * 1000)) {
    cmd /c "taskkill /PID $($proc.Id) /T /F >nul 2>&1"
    Write-Host "$Name probe: TIMEOUT (${TimeoutSeconds}s)"
    return
  }

  if ($proc.ExitCode -eq 0) {
    Write-Host "$Name probe: OK"
  } else {
    Write-Host "$Name probe: FAIL"
  }
}

# NPM sometimes fails when shell cwd is a \\?\ path; probe from a normal location.
$original = Get-Location
$probeCwd = "$env:USERPROFILE"
Set-Location $probeCwd

try {
  Write-Host ''
  Write-Host "Probe checks (cwd=$probeCwd):"

  Invoke-Probe -Name 'context7' -Command 'npx -y @upstash/context7-mcp@latest --help'
  Invoke-Probe -Name 'sequential_thinking' -Command 'npx -y @modelcontextprotocol/server-sequential-thinking --help'
  Invoke-Probe -Name 'server_fetch' -Command 'uvx mcp-server-fetch --help'
}
finally {
  Set-Location $original
}

Write-Host ''
Write-Host 'If Codex still does not list MCP resources, run fix-codex-mcp-config.ps1 then fully restart Codex.' -ForegroundColor Yellow
