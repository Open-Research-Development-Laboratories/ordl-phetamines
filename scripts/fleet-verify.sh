#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-hub}"

echo "== gateway =="
openclaw gateway status || true

echo "== node =="
openclaw node status || true

if [[ "$MODE" == "hub" ]]; then
  echo "== nodes mesh =="
  openclaw nodes pending || true
  openclaw nodes status || true
fi

echo "== devices =="
openclaw devices list || true

echo "== kimi connector =="
openclaw config get plugins.entries.kimi-claw.enabled || true
openclaw config get plugins.entries.kimi-claw.config.bridge.instanceId || true
openclaw config get plugins.entries.kimi-claw.config.bridge.deviceId || true
openclaw config get plugins.entries.kimi-claw.config.gateway.url || true
