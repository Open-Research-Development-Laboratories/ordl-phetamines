#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./fleet-bootstrap-kimi-worker.sh <WORKER_ID> <HUB_WS_URL> <HUB_TOKEN> <KIMI_TOKEN> <KIMI_USER_ID> [AGENT_ID]
# Example:
#   ./fleet-bootstrap-kimi-worker.sh worker-build-laptop ws://10.0.0.48:18789 d842... sk-... 19cb... arch

WORKER_ID="${1:-}"
HUB_WS_URL="${2:-}"
HUB_TOKEN="${3:-}"
KIMI_TOKEN="${4:-}"
KIMI_USER_ID="${5:-}"
AGENT_ID="${6:-arch}"

if [[ -z "$WORKER_ID" || -z "$HUB_WS_URL" || -z "$HUB_TOKEN" || -z "$KIMI_TOKEN" || -z "$KIMI_USER_ID" ]]; then
  echo "usage: $0 <WORKER_ID> <HUB_WS_URL> <HUB_TOKEN> <KIMI_TOKEN> <KIMI_USER_ID> [AGENT_ID]" >&2
  exit 2
fi

if ! command -v openclaw >/dev/null 2>&1; then
  echo "openclaw not found in PATH" >&2
  exit 1
fi

echo "[kimi-worker] configuring connector identity and routing..."
openclaw config set gateway.mode local
openclaw config set gateway.bind loopback
openclaw config set plugins.allow "[\"kimi-claw\",\"discord\",\"feishu\"]"
openclaw config set plugins.entries.kimi-claw.enabled true
openclaw config set plugins.entries.kimi-claw.config.bridge.mode acp
openclaw config set plugins.entries.kimi-claw.config.bridge.url wss://www.kimi.com/api-claw/bots/agent-ws
openclaw config set plugins.entries.kimi-claw.config.bridge.kimiapiHost https://www.kimi.com/api-claw
openclaw config set plugins.entries.kimi-claw.config.bridge.token "${KIMI_TOKEN}"
openclaw config set plugins.entries.kimi-claw.config.bridge.userId "${KIMI_USER_ID}"
openclaw config set plugins.entries.kimi-claw.config.bridge.instanceId "connector-${WORKER_ID}"
openclaw config set plugins.entries.kimi-claw.config.bridge.deviceId "${WORKER_ID}"
openclaw config set plugins.entries.kimi-claw.config.bridge.forwardThinking true
openclaw config set plugins.entries.kimi-claw.config.bridge.forwardToolCalls true
openclaw config set plugins.entries.kimi-claw.config.gateway.url "${HUB_WS_URL}"
openclaw config set plugins.entries.kimi-claw.config.gateway.token "${HUB_TOKEN}"
openclaw config set plugins.entries.kimi-claw.config.gateway.agentId "${AGENT_ID}"

echo "[kimi-worker] summary"
openclaw config get plugins.entries.kimi-claw.config.bridge.instanceId
openclaw config get plugins.entries.kimi-claw.config.bridge.deviceId
openclaw config get plugins.entries.kimi-claw.config.gateway.url
openclaw config get plugins.entries.kimi-claw.config.gateway.agentId

echo "[kimi-worker] run command"
echo "openclaw gateway run --bind loopback"
