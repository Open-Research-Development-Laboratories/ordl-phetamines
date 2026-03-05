#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./fleet-bootstrap-arch.sh [LAN_IP]
# Example:
#   ./fleet-bootstrap-arch.sh 10.0.0.48

if ! command -v openclaw >/dev/null 2>&1; then
  echo "openclaw not found in PATH" >&2
  exit 1
fi

LAN_IP="${1:-}"

echo "[hub-linux] configuring local gateway mode..."
openclaw config set gateway.mode local
openclaw config set gateway.bind lan
openclaw config set gateway.remote.url ws://127.0.0.1:18789
openclaw config set gateway.auth.rateLimit.maxAttempts 10
openclaw config set gateway.auth.rateLimit.windowMs 60000
openclaw config set gateway.auth.rateLimit.lockoutMs 300000

if [[ -n "$LAN_IP" ]]; then
  echo "[hub-linux] reminder: ensure allowedOrigins includes http://${LAN_IP}:18789 in ~/.openclaw/openclaw.json"
fi

echo "[hub-linux] status"
openclaw gateway status

echo "[hub-linux] gateway token"
TOKEN="$(openclaw config get gateway.auth.token || true)"
echo "$TOKEN"

echo "[hub-linux] run command"
echo "openclaw gateway run --bind lan"

echo "[hub-linux] mesh snapshot"
openclaw nodes pending || true
openclaw nodes status || true
openclaw devices list || true
