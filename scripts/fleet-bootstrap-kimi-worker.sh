#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./fleet-bootstrap-kimi-worker.sh <WORKER_ID> <HUB_WS_URL> <HUB_TOKEN> <KIMI_TOKEN> <KIMI_USER_ID> [AGENT_ID]
# Example:
#   ./fleet-bootstrap-kimi-worker.sh worker-build-laptop ws://gateway.example.internal:18789 hub-token-example kimi-token-example kimi-user-id-example arch

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

if ! command -v ordlctl >/dev/null 2>&1; then
  echo "ordlctl not found in PATH" >&2
  exit 1
fi

echo "[kimi-worker] configuring connector identity and routing..."
ordlctl config set gateway.mode local
ordlctl config set gateway.bind loopback
ordlctl config set plugins.allow "[\"kimi-claw\",\"discord\",\"feishu\"]"
ordlctl config set plugins.entries.kimi-claw.enabled true
ordlctl config set plugins.entries.kimi-claw.config.bridge.mode acp
ordlctl config set plugins.entries.kimi-claw.config.bridge.url wss://www.kimi.com/api-claw/bots/agent-ws
ordlctl config set plugins.entries.kimi-claw.config.bridge.kimiapiHost https://www.kimi.com/api-claw
ordlctl config set plugins.entries.kimi-claw.config.bridge.token "${KIMI_TOKEN}"
ordlctl config set plugins.entries.kimi-claw.config.bridge.userId "${KIMI_USER_ID}"
ordlctl config set plugins.entries.kimi-claw.config.bridge.instanceId "connector-${WORKER_ID}"
ordlctl config set plugins.entries.kimi-claw.config.bridge.deviceId "${WORKER_ID}"
ordlctl config set plugins.entries.kimi-claw.config.bridge.forwardThinking true
ordlctl config set plugins.entries.kimi-claw.config.bridge.forwardToolCalls true
ordlctl config set plugins.entries.kimi-claw.config.gateway.url "${HUB_WS_URL}"
ordlctl config set plugins.entries.kimi-claw.config.gateway.token "${HUB_TOKEN}"
ordlctl config set plugins.entries.kimi-claw.config.gateway.agentId "${AGENT_ID}"

echo "[kimi-worker] summary"
ordlctl config get plugins.entries.kimi-claw.config.bridge.instanceId
ordlctl config get plugins.entries.kimi-claw.config.bridge.deviceId
ordlctl config get plugins.entries.kimi-claw.config.gateway.url
ordlctl config get plugins.entries.kimi-claw.config.gateway.agentId

echo "[kimi-worker] run command"
echo "ordlctl gateway run --bind loopback"
