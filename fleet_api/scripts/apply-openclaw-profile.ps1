param(
  [ValidateSet("balanced", "token-saver", "high-throughput")]
  [string]$Profile = "balanced",
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command openclaw -ErrorAction SilentlyContinue)) {
  throw "openclaw CLI was not found in PATH."
}

function Set-Cfg {
  param(
    [Parameter(Mandatory = $true)][string]$Path,
    [Parameter(Mandatory = $true)]$Value,
    [switch]$Preview
  )

  $wireValue = switch ($Value.GetType().Name) {
    "Boolean" { if ($Value) { "true" } else { "false" }; break }
    "Int32" { [string]$Value; break }
    "Int64" { [string]$Value; break }
    "Double" { [string]$Value; break }
    default { [string]$Value; break }
  }

  if ($Preview) {
    Write-Output ("[dry-run] openclaw config set {0} {1}" -f $Path, $wireValue)
    return
  }

  & openclaw config set $Path $wireValue | Out-Null
}

switch ($Profile) {
  "balanced" {
    $target = [ordered]@{
      "agents.defaults.maxConcurrent" = 4
      "agents.defaults.subagents.maxConcurrent" = 8
      "agents.defaults.bootstrapMaxChars" = 18000
      "agents.defaults.bootstrapTotalMaxChars" = 100000
      "agents.defaults.imageMaxDimensionPx" = 1200
      "agents.defaults.heartbeat.every" = "55m"
      "agents.defaults.compaction.mode" = "safeguard"
      "agents.defaults.contextPruning.mode" = "cache-ttl"
      "agents.defaults.contextPruning.ttl" = "1h"
      "tools.web.search.enabled" = $true
      "tools.web.search.maxResults" = 5
      "tools.web.fetch.enabled" = $true
      "tools.web.fetch.maxChars" = 30000
      "tools.web.fetch.maxCharsCap" = 30000
      "hooks.enabled" = $true
      "channels.discord.enabled" = $true
      "logging.consoleStyle" = "compact"
      "plugins.entries.kimi-claw.config.bridge.forwardThinking" = $true
      "plugins.entries.kimi-claw.config.bridge.forwardToolCalls" = $true
    }
  }
  "token-saver" {
    $target = [ordered]@{
      "agents.defaults.maxConcurrent" = 2
      "agents.defaults.subagents.maxConcurrent" = 3
      "agents.defaults.bootstrapMaxChars" = 12000
      "agents.defaults.bootstrapTotalMaxChars" = 60000
      "agents.defaults.imageMaxDimensionPx" = 900
      "agents.defaults.heartbeat.every" = "0m"
      "agents.defaults.compaction.mode" = "safeguard"
      "agents.defaults.contextPruning.mode" = "cache-ttl"
      "agents.defaults.contextPruning.ttl" = "1h"
      "tools.web.search.enabled" = $true
      "tools.web.search.maxResults" = 3
      "tools.web.fetch.enabled" = $true
      "tools.web.fetch.maxChars" = 15000
      "tools.web.fetch.maxCharsCap" = 15000
      "hooks.enabled" = $false
      "channels.discord.enabled" = $false
      "logging.consoleStyle" = "compact"
      "plugins.entries.kimi-claw.config.bridge.forwardThinking" = $false
      "plugins.entries.kimi-claw.config.bridge.forwardToolCalls" = $true
    }
  }
  "high-throughput" {
    $target = [ordered]@{
      "agents.defaults.maxConcurrent" = 8
      "agents.defaults.subagents.maxConcurrent" = 12
      "agents.defaults.bootstrapMaxChars" = 22000
      "agents.defaults.bootstrapTotalMaxChars" = 150000
      "agents.defaults.imageMaxDimensionPx" = 1400
      "agents.defaults.heartbeat.every" = "30m"
      "agents.defaults.compaction.mode" = "safeguard"
      "agents.defaults.contextPruning.mode" = "cache-ttl"
      "agents.defaults.contextPruning.ttl" = "30m"
      "tools.web.search.enabled" = $true
      "tools.web.search.maxResults" = 8
      "tools.web.fetch.enabled" = $true
      "tools.web.fetch.maxChars" = 50000
      "tools.web.fetch.maxCharsCap" = 50000
      "hooks.enabled" = $true
      "channels.discord.enabled" = $true
      "logging.consoleStyle" = "pretty"
      "plugins.entries.kimi-claw.config.bridge.forwardThinking" = $true
      "plugins.entries.kimi-claw.config.bridge.forwardToolCalls" = $true
    }
  }
}

foreach ($kv in $target.GetEnumerator()) {
  Set-Cfg -Path $kv.Key -Value $kv.Value -Preview:$DryRun
}

if (-not $DryRun) {
  & openclaw config validate | Out-Null
}

$summary = [ordered]@{
  profile = $Profile
  dry_run = [bool]$DryRun
  changed = $target.Keys.Count
  restart_required = (-not $DryRun)
  note = "Restart gateway after apply: openclaw gateway stop ; OPENCLAW_SKIP_GMAIL_WATCHER=1 openclaw gateway run --bind lan"
}

$summary | ConvertTo-Json -Depth 4
