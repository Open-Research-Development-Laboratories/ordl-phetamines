#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-hub}"

echo "== gateway =="
ordlctl gateway status || true

echo "== node =="
ordlctl node status || true

if [[ "$MODE" == "hub" ]]; then
  echo "== nodes mesh =="
  ordlctl nodes pending || true
  ordlctl nodes status || true
fi

echo "== devices =="
ordlctl devices list || true

echo "== kimi connector =="
ordlctl config get plugins.entries.kimi-claw.enabled || true
ordlctl config get plugins.entries.kimi-claw.config.bridge.instanceId || true
ordlctl config get plugins.entries.kimi-claw.config.bridge.deviceId || true
ordlctl config get plugins.entries.kimi-claw.config.gateway.url || true
