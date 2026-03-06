#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="${1:-ordlctl-worker.service}"
LOG_FILE="${2:-$HOME/ordlctl-worker.log}"

mkdir -p "$HOME/.config/systemd/user"

cat > "$HOME/.config/systemd/user/$SERVICE_NAME" <<EOF
[Unit]
Description=ordlctl Kimi Worker Gateway
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStartPre=/usr/bin/env bash -lc 'pkill -x ordlctl-gateway || true'
ExecStart=/usr/bin/env bash -lc 'ordlctl gateway run --bind loopback'
Restart=always
RestartSec=5
StandardOutput=append:${LOG_FILE}
StandardError=append:${LOG_FILE}

[Install]
WantedBy=default.target
EOF

if command -v systemctl >/dev/null 2>&1; then
  systemctl --user daemon-reload || true
  systemctl --user enable --now "$SERVICE_NAME" || true
  systemctl --user status "$SERVICE_NAME" --no-pager || true
else
  echo "systemctl not available; install user cron fallback manually."
fi

echo "Installed ${SERVICE_NAME}"
