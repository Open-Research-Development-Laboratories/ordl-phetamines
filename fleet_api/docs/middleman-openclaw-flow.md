# Fleet Middle-Man Flow (OpenClaw Chat First)

This is the standard operating flow for your crew:

1. Workers generate their reports.
2. Reports are dumped into OpenClaw chat as **UNREVIEWED WORKER DUMP**.
3. Human-in-the-middle reviews/edits in chat.
4. You can request rework with reviewer feedback.
5. Revised worker reports are restaged into the same OpenClaw chat pipeline.
6. Repeat until accepted, then finalize.

This intentionally avoids app-internal clickable links (`app://...`) and uses direct commands.

## Prereqs

- Desktop hub/gateway running.
- Fleet API running.
- `FLEET_SSH_PASSWORD` set in the shell that runs fleet scripts.
- Worker reports exist under `/development/crew-handoff/*.md`.

## One Command (Stage to Chat)

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\Winsock\Documents\GitHub\ordl-phetamines\fleet_api\scripts\run-middleman-cycle.ps1
```

If prompt entry is flaky, pass password explicitly:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\Winsock\Documents\GitHub\ordl-phetamines\fleet_api\scripts\run-middleman-cycle.ps1 -SshPassword 'War7!HolyOptSysGo'
```

What this does:

- calls `stage-worker-reports-to-openclaw-chat.ps1`
- stages latest worker handoff files into the active OpenClaw session
- enters a loop:
  - review in chat
  - choose `R` to request rework
  - enter feedback
  - workers produce revised report
  - revised reports are restaged to chat
  - choose `D` when done

## Direct Command (No Wrapper)

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\Winsock\Documents\GitHub\ordl-phetamines\fleet_api\scripts\stage-worker-reports-to-openclaw-chat.ps1
```

## Direct Rework Command

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\Winsock\Documents\GitHub\ordl-phetamines\fleet_api\scripts\rework-worker-reports.ps1 -Feedback "Tighten claims, add scripture citations, remove repetition"
```

## API Trigger

```powershell
$h = @{ "X-API-Key" = $env:FLEET_API_KEY; "Content-Type" = "application/json" }
$body = '{"async":false,"roles":["worker-build-laptop","worker-batch-server"],"handoff_glob":"/development/crew-handoff/*.md","max_chars":2500}'
Invoke-RestMethod http://127.0.0.1:8890/v1/fleet/stage-handoff -Method Post -Headers $h -Body $body
```

## Verification

Check session recency:

```powershell
openclaw sessions --json
```

If staging worked, the session `updatedAt` will move forward right after the command.

## Failure Modes

- `FLEET_SSH_PASSWORD is required for remote orchestration`
  - Restart Fleet API with `FLEET_SSH_PASSWORD` in its process environment.
- `Authentication failed`
  - Re-run with `-SshPassword '...'` to avoid prompt paste/input issues.
- `no handoff files matched /development/crew-handoff/*.md`
  - Workers have not produced report files yet; generate reports first.
- `origin not allowed`
  - open control UI locally, or add tunnel origin to `gateway.controlUi.allowedOrigins`.

## Operator Rule

Do not finalize from agent side until the middle-man confirms chat review is complete.
