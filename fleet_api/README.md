# Fleet API

Flask control plane for your OpenClaw/Kimi fleet.

It wraps:
- Worker SSH orchestration (status, restart, resync, corpus sync)
- Desktop OpenClaw pairing approvals
- Dispatch contract build/validation
- Local policy snapshot/tests/decisions
- Async jobs with status tracking

## Quick Start

From repo root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r .\fleet_api\requirements.txt
```

Set environment:

```powershell
$env:FLEET_API_KEY = "set-a-real-key"
$env:FLEET_SSH_PASSWORD = "your-worker-ssh-password"
$env:FLEET_WORKSPACE_ROOT = "C:\development"
$env:FLEET_LAPTOP_HOST = "10.0.0.28"
$env:FLEET_SERVER_HOST = "10.0.0.27"
$env:FLEET_HUB_HOST = "10.0.0.48"
$env:FLEET_STATUS_MAX_PARALLEL = "4"
$env:FLEET_HEALTH_SIGNAL_RECENCY_MINUTES = "180"
$env:CLOUDFLARE_TUNNEL_TOKEN = "optional-named-tunnel-token"
```

Run:

```powershell
python .\fleet_api\run.py
```

Desktop autostart:

```powershell
powershell -ExecutionPolicy Bypass -File .\fleet_api\scripts\install-desktop-autostart.ps1
```

Desktop autostart (OpenClaw hub + API + Cloudflare tunnel):

```powershell
powershell -ExecutionPolicy Bypass -File .\fleet_api\scripts\install-all-autostart.ps1
```

Linux worker autostart:

```bash
bash /path/to/repo/fleet_api/scripts/install-linux-worker-autostart.sh
```

One-shot token resync to workers (no manual copy/paste):

```powershell
powershell -ExecutionPolicy Bypass -File .\fleet_api\scripts\resync-fleet-tokens.ps1
```

Specific roles only:

```powershell
powershell -ExecutionPolicy Bypass -File .\fleet_api\scripts\resync-fleet-tokens.ps1 -Roles worker-build-laptop,worker-batch-server
```

Stage latest worker handoff reports into OpenClaw chat (for human-in-the-middle review):

```powershell
powershell -ExecutionPolicy Bypass -File .\fleet_api\scripts\stage-worker-reports-to-openclaw-chat.ps1
```

Run full middle-man checkpoint cycle (stage then operator pause):

```powershell
powershell -ExecutionPolicy Bypass -File .\fleet_api\scripts\run-middleman-cycle.ps1
```

If needed, pass worker SSH password directly:

```powershell
powershell -ExecutionPolicy Bypass -File .\fleet_api\scripts\run-middleman-cycle.ps1 -SshPassword 'War7!HolyOptSysGo'
```

UI:
- <http://127.0.0.1:8890/>

Health:
- `GET /health`

## API Endpoints

Auth:
- Pass `X-API-Key: <key>` for `/v1/*` endpoints.

Core:
- `GET /v1/info`
- `GET /v1/jobs`
- `GET /v1/jobs/{job_id}`

Fleet:
- `GET /v1/fleet/status`
- `GET /v1/fleet/health`
- `POST /v1/fleet/restart`
- `POST /v1/fleet/resync`
- `POST /v1/fleet/sync-corpus`
- `POST /v1/fleet/verify-corpus`
- `GET /v1/fleet/logs/{role}`
- `POST /v1/fleet/command` (disabled by default; set `FLEET_ENABLE_REMOTE_COMMAND=true`)
- `POST /v1/fleet/stage-handoff`

Dispatch:
- `POST /v1/dispatch/build`
- `POST /v1/dispatch/validate`

Policy:
- `GET /v1/policy/snapshot`
- `POST /v1/policy/tests`
- `POST /v1/policy/decide`

Playbooks:
- `GET /v1/playbooks`

## Example Calls

```powershell
$h = @{ "X-API-Key" = $env:FLEET_API_KEY; "Content-Type" = "application/json" }
Invoke-RestMethod http://127.0.0.1:8890/v1/fleet/status -Headers $h
Invoke-RestMethod http://127.0.0.1:8890/v1/fleet/health -Headers $h
Invoke-RestMethod "http://127.0.0.1:8890/v1/fleet/health?recency_minutes=120" -Headers $h
Invoke-RestMethod http://127.0.0.1:8890/v1/fleet/resync -Method Post -Headers $h -Body '{"async":true}'
Invoke-RestMethod http://127.0.0.1:8890/v1/policy/tests -Method Post -Headers $h -Body '{"async":true}'
Invoke-RestMethod http://127.0.0.1:8890/v1/fleet/stage-handoff -Method Post -Headers $h -Body '{"async":true}'
```

## Notes

- Resync pulls token values from local desktop `openclaw config get ...` outputs and pushes them to workers.
- Corpus sync may fail on root-owned remote files; the API reports each failed path so you can correct permissions.
- `start-cloudflared.ps1` uses named tunnel mode when `CLOUDFLARE_TUNNEL_TOKEN` is set, else quick tunnel mode.
- `start-openclaw-hub.ps1` starts `openclaw gateway run --bind lan` for worker connectivity.
- Run `install-linux-worker-autostart.sh` on each Linux worker host (laptop/server) to survive reboot.
- Job events are written to:
  - `fleet_api/state/jobs-events.jsonl`
- Middle-man flow runbook:
  - `fleet_api/docs/middleman-openclaw-flow.md`
