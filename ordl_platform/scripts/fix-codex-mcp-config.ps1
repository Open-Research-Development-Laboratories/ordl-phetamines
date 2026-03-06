$config = "$env:USERPROFILE\.codex\config.toml"
if (!(Test-Path $config)) {
  Write-Error "Config not found: $config"
  exit 1
}

$raw = Get-Content $config -Raw

# Normalize npx args that were accidentally combined into a single string.
$raw = $raw -replace 'args\s*=\s*\["-y\s+@upstash/context7-mcp@latest"\]', 'args = ["-y", "@upstash/context7-mcp@latest"]'
$raw = $raw -replace 'args\s*=\s*\["-y\s+@modelcontextprotocol/server-sequential-thinking"\]', 'args = ["-y", "@modelcontextprotocol/server-sequential-thinking"]'

# Ensure cwd entries don't end in trailing slash escape weirdness.
$raw = $raw -replace "cwd\s*=\s*'C:\\development\\'", "cwd = 'C:\\development'"

Set-Content -Path $config -Value $raw
Write-Host 'Updated MCP config formatting for context7 and sequential_thinking.' -ForegroundColor Green
Write-Host 'Restart Codex app after this change.' -ForegroundColor Yellow
