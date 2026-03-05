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
POLICY_ALERT_DISCORD_TARGET='channel:1379869405164343353' \
POLICY_ALERT_EMAIL_TO='you@example.com' \
node policy/gateway-server.js
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
- Discord ping/message via `openclaw message send`
- Email via local `sendmail` when `POLICY_ALERT_EMAIL_TO` is set
- Audit record in `policy/audit.log`
- Block queue in `policy/blocked-queue.jsonl`
- Status signal in `policy/status.json` (red when blocked)

## Event format
Use `specs/policy-schema.json`.

## Security notes
- Fail closed: if gateway is down, sends fail.
- Do not send directly to provider APIs from automations.
- Route all outbound automations through `guarded-send.js` or equivalent adapter.

## Current scope
This enforces automated sends routed through this wrapper.
To make it universal for every agent action, integrate this decision call into OpenClaw outbound send path/plugin middleware.
