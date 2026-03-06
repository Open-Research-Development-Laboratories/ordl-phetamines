# ordlctl Runtime Profiles

This repo includes profile scripts to tune ordlctl for token efficiency or throughput:

- Windows: `fleet_api/scripts/apply-gateway-profile.ps1`
- Linux: `fleet_api/scripts/apply-gateway-profile.sh`
- Windows plugin guard: `fleet_api/scripts/ensure-required-plugins.ps1`
- Linux plugin guard: `fleet_api/scripts/ensure-required-plugins.sh`

## Profile goals

- `token-saver`: lowest steady token burn for always-on fleet operations.
- `balanced`: good default for day-to-day engineering + orchestration.
- `high-throughput`: higher parallelism and richer context for heavy runs.

## What gets tuned

- Agent parallelism:
  - `agents.defaults.maxConcurrent`
  - `agents.defaults.subagents.maxConcurrent`
- Prompt/context size controls:
  - `agents.defaults.bootstrapMaxChars`
  - `agents.defaults.bootstrapTotalMaxChars`
  - `agents.defaults.imageMaxDimensionPx`
- Lifecycle + token controls:
  - `agents.defaults.heartbeat.every`
  - `agents.defaults.compaction.mode`
  - `agents.defaults.contextPruning.mode`
  - `agents.defaults.contextPruning.ttl`
- Web tool budget:
  - `tools.web.search.maxResults`
  - `tools.web.fetch.maxChars`
  - `tools.web.fetch.maxCharsCap`
- Fleet behavior:
  - `hooks.enabled`
  - `channels.discord.enabled`
  - `plugins.entries.kimi-claw.config.bridge.forwardThinking`
  - `plugins.entries.kimi-claw.config.bridge.forwardToolCalls`
  - `logging.consoleStyle`

## Usage

### Windows (desktop)

Dry run:

```powershell
powershell -ExecutionPolicy Bypass -File .\fleet_api\scripts\apply-gateway-profile.ps1 -Profile token-saver -DryRun
```

Apply:

```powershell
powershell -ExecutionPolicy Bypass -File .\fleet_api\scripts\apply-gateway-profile.ps1 -Profile balanced
```

Ensure required plugins (`kimi-claw`, `discord`, `memory-core`) are discoverable + pinned:

```powershell
powershell -ExecutionPolicy Bypass -File .\fleet_api\scripts\ensure-required-plugins.ps1
```

### Linux (workers)

Dry run:

```bash
DRY_RUN=1 bash ./fleet_api/scripts/apply-gateway-profile.sh token-saver
```

Apply:

```bash
bash ./fleet_api/scripts/apply-gateway-profile.sh balanced
```

Ensure required plugins (`kimi-claw`, `discord`, `memory-core`) are discoverable + pinned:

```bash
bash ./fleet_api/scripts/ensure-required-plugins.sh
```

## Restart after apply

Runtime changes require gateway restart.

Desktop (LAN hub):

```powershell
ordlctl gateway stop
ordlctl gateway run --bind lan
```

Worker (loopback):

```bash
ordlctl gateway stop || true
pkill -f ordlctl-gateway || true
nohup ordlctl gateway run --bind loopback > ~/ordlctl-worker.log 2>&1 &
```
