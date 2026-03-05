#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./fleet-bootstrap-node.sh <HUB_HOST> <HUB_TOKEN> [LOCAL_TUNNEL_PORT]
# Example:
#   ./fleet-bootstrap-node.sh 10.0.0.48 d842... 55556

HUB_HOST="${1:-}"
HUB_TOKEN="${2:-}"
LOCAL_PORT="${3:-55556}"

if [[ -z "$HUB_HOST" || -z "$HUB_TOKEN" ]]; then
  echo "usage: $0 <HUB_HOST> <HUB_TOKEN> [LOCAL_TUNNEL_PORT]" >&2
  exit 2
fi

if ! command -v openclaw >/dev/null 2>&1; then
  echo "openclaw not found in PATH" >&2
  exit 1
fi

echo "[node] configuring local remote target through SSH tunnel..."
openclaw config set gateway.mode remote
openclaw config set gateway.remote.url "ws://127.0.0.1:${LOCAL_PORT}"
openclaw config set gateway.remote.token "${HUB_TOKEN}"

echo "[node] ensuring node unit exists..."
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/openclaw-node.service <<EOF
[Unit]
Description=OpenClaw Node Host
After=default.target

[Service]
Type=simple
ExecStart=/usr/bin/env bash -lc 'openclaw node run --host 127.0.0.1 --port ${LOCAL_PORT}'
Restart=always
RestartSec=2
Environment=HOME=/home/$USER
Environment=PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/home/$USER/.npm-global/bin
Environment=OPENCLAW_GATEWAY_TOKEN=${HUB_TOKEN}

[Install]
WantedBy=default.target
EOF

echo "[node] restarting node service..."
systemctl --user daemon-reload
systemctl --user enable --now openclaw-node.service

# kill old local forwards for chosen port
pkill -f "ssh -N -L ${LOCAL_PORT}:127.0.0.1:18789" || true

echo "[node] opening tunnel to hub (${HUB_HOST}) local:${LOCAL_PORT} -> hub:18789"
ssh -fN -L ${LOCAL_PORT}:127.0.0.1:18789 "${USER}@${HUB_HOST}" || {
  echo "tunnel failed; run manually:" >&2
  echo "ssh -N -L ${LOCAL_PORT}:127.0.0.1:18789 ${USER}@${HUB_HOST}" >&2
  exit 1
}

echo "[node] recent logs"
journalctl --user -u openclaw-node.service -n 25 --no-pager || true

echo "[node] done; approve on hub with: openclaw devices approve"
