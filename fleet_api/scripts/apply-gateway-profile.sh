#!/usr/bin/env bash
set -euo pipefail

PROFILE="${1:-balanced}"
DRY_RUN="${DRY_RUN:-0}"

if ! command -v ordlctl >/dev/null 2>&1; then
  echo "ordlctl CLI was not found in PATH." >&2
  exit 1
fi

apply_cfg() {
  local path="$1"
  local value="$2"

  if [[ "${DRY_RUN}" == "1" ]]; then
    echo "[dry-run] ordlctl config set ${path} ${value}"
    return 0
  fi

  ordlctl config set "${path}" "${value}" >/dev/null
}

case "${PROFILE}" in
  balanced)
    PAIRS="$(cat <<'EOF'
agents.defaults.maxConcurrent|4
agents.defaults.subagents.maxConcurrent|8
agents.defaults.bootstrapMaxChars|18000
agents.defaults.bootstrapTotalMaxChars|100000
agents.defaults.imageMaxDimensionPx|1200
agents.defaults.heartbeat.every|"55m"
agents.defaults.compaction.mode|"safeguard"
agents.defaults.contextPruning.mode|"cache-ttl"
agents.defaults.contextPruning.ttl|"1h"
tools.web.search.enabled|true
tools.web.search.maxResults|5
tools.web.fetch.enabled|true
tools.web.fetch.maxChars|30000
tools.web.fetch.maxCharsCap|30000
hooks.enabled|true
channels.discord.enabled|true
logging.consoleStyle|"compact"
plugins.entries.kimi-claw.config.bridge.forwardThinking|true
plugins.entries.kimi-claw.config.bridge.forwardToolCalls|true
EOF
)"
    ;;
  token-saver)
    PAIRS="$(cat <<'EOF'
agents.defaults.maxConcurrent|2
agents.defaults.subagents.maxConcurrent|3
agents.defaults.bootstrapMaxChars|12000
agents.defaults.bootstrapTotalMaxChars|60000
agents.defaults.imageMaxDimensionPx|900
agents.defaults.heartbeat.every|"0m"
agents.defaults.compaction.mode|"safeguard"
agents.defaults.contextPruning.mode|"cache-ttl"
agents.defaults.contextPruning.ttl|"1h"
tools.web.search.enabled|true
tools.web.search.maxResults|3
tools.web.fetch.enabled|true
tools.web.fetch.maxChars|15000
tools.web.fetch.maxCharsCap|15000
hooks.enabled|false
channels.discord.enabled|false
logging.consoleStyle|"compact"
plugins.entries.kimi-claw.config.bridge.forwardThinking|false
plugins.entries.kimi-claw.config.bridge.forwardToolCalls|true
EOF
)"
    ;;
  high-throughput)
    PAIRS="$(cat <<'EOF'
agents.defaults.maxConcurrent|8
agents.defaults.subagents.maxConcurrent|12
agents.defaults.bootstrapMaxChars|22000
agents.defaults.bootstrapTotalMaxChars|150000
agents.defaults.imageMaxDimensionPx|1400
agents.defaults.heartbeat.every|"30m"
agents.defaults.compaction.mode|"safeguard"
agents.defaults.contextPruning.mode|"cache-ttl"
agents.defaults.contextPruning.ttl|"30m"
tools.web.search.enabled|true
tools.web.search.maxResults|8
tools.web.fetch.enabled|true
tools.web.fetch.maxChars|50000
tools.web.fetch.maxCharsCap|50000
hooks.enabled|true
channels.discord.enabled|true
logging.consoleStyle|"pretty"
plugins.entries.kimi-claw.config.bridge.forwardThinking|true
plugins.entries.kimi-claw.config.bridge.forwardToolCalls|true
EOF
)"
    ;;
  *)
    echo "Unknown profile: ${PROFILE}. Use: balanced | token-saver | high-throughput" >&2
    exit 2
    ;;
esac

changed=0
while IFS='|' read -r path value; do
  [[ -z "${path}" ]] && continue
  apply_cfg "${path}" "${value}"
  changed=$((changed + 1))
done <<< "${PAIRS}"

if [[ "${DRY_RUN}" != "1" ]]; then
  ordlctl config validate >/dev/null
fi

cat <<EOF
{
  "profile": "${PROFILE}",
  "dry_run": $([[ "${DRY_RUN}" == "1" ]] && echo "true" || echo "false"),
  "changed": ${changed},
  "restart_required": $([[ "${DRY_RUN}" == "1" ]] && echo "false" || echo "true"),
  "note": "Restart gateway after apply: ordlctl gateway stop ; ordlctl gateway run --bind loopback"
}
EOF
