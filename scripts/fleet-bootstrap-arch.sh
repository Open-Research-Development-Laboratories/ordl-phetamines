#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./fleet-bootstrap-arch.sh [LAN_IP]
# Example:
#   ./fleet-bootstrap-arch.sh 10.0.0.48

if ! command -v ordlctl >/dev/null 2>&1; then
  echo "ordlctl not found in PATH" >&2
  exit 1
fi

LAN_IP="${1:-}"

echo "[hub-linux] configuring local gateway mode..."
ordlctl config set gateway.mode local
ordlctl config set gateway.bind lan
ordlctl config set gateway.remote.url ws://127.0.0.1:18789
ordlctl config set gateway.auth.rateLimit.maxAttempts 10
ordlctl config set gateway.auth.rateLimit.windowMs 60000
ordlctl config set gateway.auth.rateLimit.lockoutMs 300000

if [[ -n "$LAN_IP" ]]; then
  echo "[hub-linux] reminder: ensure allowedOrigins includes http://${LAN_IP}:18789 in ~/.ordlctl/ordlctl.json"
fi

echo "[hub-linux] status"
ordlctl gateway status

echo "[hub-linux] gateway token"
TOKEN="$(ordlctl config get gateway.auth.token || true)"
echo "$TOKEN"

echo "[hub-linux] run command"
echo "ordlctl gateway run --bind lan"

echo "[hub-linux] mesh snapshot"
ordlctl nodes pending || true
ordlctl nodes status || true
ordlctl devices list || true
