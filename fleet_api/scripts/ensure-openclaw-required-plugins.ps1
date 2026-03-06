param(
  [string[]]$RequiredPlugins = @("kimi-claw", "discord", "memory-core"),
  [switch]$SkipValidate
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command openclaw -ErrorAction SilentlyContinue)) {
  throw "openclaw CLI was not found in PATH."
}

$ConfigPath = Join-Path $HOME ".openclaw\\openclaw.json"
if (-not (Test-Path $ConfigPath)) {
  throw "OpenClaw config not found at $ConfigPath"
}

function Get-PluginIds {
  try {
    $raw = & openclaw plugins list --json
    $obj = $raw | ConvertFrom-Json
    return @($obj.plugins | ForEach-Object { $_.id } | Where-Object { $_ -and $_.Trim() } | ForEach-Object { $_.Trim() } | Select-Object -Unique)
  } catch {
    return @()
  }
}

function Read-ConfigObject {
  $raw = Get-Content $ConfigPath -Raw -Encoding utf8
  if ($raw.Length -gt 0 -and $raw[0] -eq [char]0xFEFF) {
    $raw = $raw.Substring(1)
  }
  return ($raw | ConvertFrom-Json)
}

function Write-ConfigObject {
  param([Parameter(Mandatory = $true)]$Config)
  $json = $Config | ConvertTo-Json -Depth 100
  Set-Content -Path $ConfigPath -Value $json -Encoding utf8
}

function Ensure-ObjectProperty {
  param(
    [Parameter(Mandatory = $true)]$Object,
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)]$DefaultValue
  )
  if (-not ($Object.PSObject.Properties.Name -contains $Name) -or $null -eq $Object.$Name) {
    $Object | Add-Member -NotePropertyName $Name -NotePropertyValue $DefaultValue -Force
  }
}

function Resolve-BundledPluginsDir {
  if ($env:OPENCLAW_BUNDLED_PLUGINS_DIR -and (Test-Path $env:OPENCLAW_BUNDLED_PLUGINS_DIR)) {
    return (Resolve-Path $env:OPENCLAW_BUNDLED_PLUGINS_DIR).Path
  }

  $cmdSource = (Get-Command openclaw).Source
  $shimDir = Split-Path $cmdSource -Parent
  $candidates = @(
    (Join-Path $shimDir "node_modules\\openclaw\\extensions"),
    (Join-Path $env:APPDATA "npm\\node_modules\\openclaw\\extensions"),
    (Join-Path $env:ProgramFiles "OpenClaw\\resources\\extensions")
  )

  foreach ($candidate in $candidates) {
    if ($candidate -and (Test-Path $candidate)) {
      return (Resolve-Path $candidate).Path
    }
  }

  return $null
}

$config = Read-ConfigObject
Ensure-ObjectProperty -Object $config -Name "plugins" -DefaultValue ([pscustomobject]@{})
Ensure-ObjectProperty -Object $config.plugins -Name "load" -DefaultValue ([pscustomobject]@{})
Ensure-ObjectProperty -Object $config.plugins.load -Name "paths" -DefaultValue @()
Ensure-ObjectProperty -Object $config.plugins -Name "slots" -DefaultValue ([pscustomobject]@{})
Ensure-ObjectProperty -Object $config.plugins -Name "allow" -DefaultValue @()
Ensure-ObjectProperty -Object $config -Name "channels" -DefaultValue ([pscustomobject]@{})
Ensure-ObjectProperty -Object $config.channels -Name "discord" -DefaultValue ([pscustomobject]@{})

$pluginIds = Get-PluginIds
$missing = @($RequiredPlugins | Where-Object { $pluginIds -notcontains $_ })
$changed = $false
$bundledDirAdded = $false

if ($missing.Count -gt 0) {
  $bundledDir = Resolve-BundledPluginsDir
  if ($bundledDir) {
    $paths = @($config.plugins.load.paths | ForEach-Object { "$_".Trim() } | Where-Object { $_ })
    if ($paths -notcontains $bundledDir) {
      $paths += $bundledDir
      $config.plugins.load.paths = $paths
      $changed = $true
      $bundledDirAdded = $true
    }
  }
}

if ($changed) {
  Write-ConfigObject -Config $config
}

$pluginIds = Get-PluginIds
$missing = @($RequiredPlugins | Where-Object { $pluginIds -notcontains $_ })
if ($missing.Count -gt 0) {
  throw ("Missing required plugins on this host: {0}. Install/copy them first, then rerun." -f ($missing -join ", "))
}

$allow = @($config.plugins.allow | ForEach-Object { "$_".Trim() } | Where-Object { $_ } | Select-Object -Unique)
foreach ($id in $RequiredPlugins) {
  if ($allow -notcontains $id) {
    $allow += $id
    $changed = $true
  }
}
$config.plugins.allow = $allow

if ($config.plugins.slots.memory -ne "memory-core") {
  $config.plugins.slots.memory = "memory-core"
  $changed = $true
}

if ($config.channels.discord.enabled -ne $true) {
  $config.channels.discord.enabled = $true
  $changed = $true
}

if ($changed) {
  Write-ConfigObject -Config $config
}

if (-not $SkipValidate) {
  & openclaw config validate --json | Out-Null
}

$summary = [ordered]@{
  config_path = $ConfigPath
  required_plugins = $RequiredPlugins
  bundled_dir_added = $bundledDirAdded
  changed = $changed
  restart_required = $true
  restart_cmd = "openclaw gateway stop; OPENCLAW_SKIP_GMAIL_WATCHER=1 openclaw gateway run --bind loopback"
}

$summary | ConvertTo-Json -Depth 10
