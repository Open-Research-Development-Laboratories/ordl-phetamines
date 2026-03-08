# Universal Policy Gateway (enforcement path)

This is the enforcement layer for outbound messaging.

## Components
- `engine.js` deterministic policy engine
- `gateway-server.js` local decision API (`/decide`)
- `guarded-send.js` send wrapper that blocks unless decision is `allow`

## Run

1) Start gateway

```bash
POLICY_GATEWAY_SECRET='set-strong-secret' \
POLICY_ALERT_EMAIL_TO='you@example.com' \
node policy/gateway-server.js
```

Optional alert routing:

```bash
export POLICY_ALERT_DISCORD_TARGET='channel:example-policy-alerts'
```

2) Send through gate

```bash
node policy/guarded-send.js /path/to/event.json
```

## Endpoints
- `GET /health`
- `GET /status` (UI bar state: green/yellow/red)
- `POST /decide` (policy decision)
- `POST /reevaluate` (manual reevaluation with full `event` payload)

## Alert fanout on block/hold
- Discord ping/message via `ordlctl message send`
- Email via local `sendmail` when `POLICY_ALERT_EMAIL_TO` is set
- Audit record in `policy/runtime/audit.log`
- Block queue in `policy/runtime/blocked-queue.jsonl`
- Status signal in `policy/runtime/status.json` (red when blocked)

## Event format
Use `specs/policy-schema.json`.

## Security notes
- Fail closed: if gateway is down, sends fail.
- Do not send directly to provider APIs from automations.
- Route all outbound automations through `guarded-send.js` or equivalent adapter.
- Runtime outputs are intentionally excluded from git tracking.

## Current scope
This enforces automated sends routed through this wrapper.
To make it universal for every agent action, integrate this decision call into ordlctl outbound send path/plugin middleware.
