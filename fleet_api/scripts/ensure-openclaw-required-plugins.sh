#!/usr/bin/env bash
set -euo pipefail

required_plugins=("kimi-claw" "discord" "memory-core")
config_path="${HOME}/.openclaw/openclaw.json"

if ! command -v openclaw >/dev/null 2>&1; then
  echo "openclaw CLI was not found in PATH." >&2
  exit 1
fi

if [[ ! -f "${config_path}" ]]; then
  echo "OpenClaw config not found at ${config_path}" >&2
  exit 1
fi

get_plugin_ids() {
  openclaw plugins list --json | python3 - <<'PY'
import json, sys
obj = json.load(sys.stdin)
plugins = obj.get("plugins") or []
ids = []
for p in plugins:
    pid = (p or {}).get("id")
    if isinstance(pid, str) and pid.strip():
        ids.append(pid.strip())
print("\n".join(sorted(set(ids))))
PY
}

resolve_bundled_dir() {
  if [[ -n "${OPENCLAW_BUNDLED_PLUGINS_DIR:-}" && -d "${OPENCLAW_BUNDLED_PLUGINS_DIR}" ]]; then
    printf '%s\n' "${OPENCLAW_BUNDLED_PLUGINS_DIR}"
    return 0
  fi

  local shim_dir
  shim_dir="$(cd "$(dirname "$(command -v openclaw)")" && pwd)"
  local candidates=(
    "${shim_dir}/node_modules/openclaw/extensions"
    "/usr/local/lib/node_modules/openclaw/extensions"
    "/usr/lib/node_modules/openclaw/extensions"
  )

  if command -v npm >/dev/null 2>&1; then
    local npm_root
    npm_root="$(npm root -g 2>/dev/null || true)"
    if [[ -n "${npm_root}" ]]; then
      candidates+=("${npm_root}/openclaw/extensions")
    fi
  fi

  local c
  for c in "${candidates[@]}"; do
    if [[ -d "${c}" ]]; then
      printf '%s\n' "${c}"
      return 0
    fi
  done

  return 1
}

python_set_load_path() {
  local path_to_add="$1"
  python3 - "${config_path}" "${path_to_add}" <<'PY'
import json, pathlib, sys
cfg_path = pathlib.Path(sys.argv[1])
path_to_add = sys.argv[2]
cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
plugins = cfg.setdefault("plugins", {})
load = plugins.setdefault("load", {})
paths = load.setdefault("paths", [])
norm = [str(p).strip() for p in paths if str(p).strip()]
if path_to_add not in norm:
    norm.append(path_to_add)
    load["paths"] = norm
    cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    print("changed")
else:
    print("unchanged")
PY
}

python_apply_required() {
  local req_csv="$1"
  python3 - "${config_path}" "${req_csv}" <<'PY'
import json, pathlib, sys
cfg_path = pathlib.Path(sys.argv[1])
required = [x for x in sys.argv[2].split(",") if x]
cfg = json.loads(cfg_path.read_text(encoding="utf-8"))

plugins = cfg.setdefault("plugins", {})
allow = plugins.get("allow") or []
allow_norm = []
for v in allow:
    s = str(v).strip()
    if s and s not in allow_norm:
        allow_norm.append(s)
for r in required:
    if r not in allow_norm:
        allow_norm.append(r)
plugins["allow"] = allow_norm

slots = plugins.setdefault("slots", {})
slots["memory"] = "memory-core"

channels = cfg.setdefault("channels", {})
discord = channels.setdefault("discord", {})
discord["enabled"] = True

cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
print("changed")
PY
}

contains_id() {
  local needle="$1"
  local ids="$2"
  grep -Fxq "${needle}" <<<"${ids}"
}

ids="$(get_plugin_ids || true)"
missing=()
for p in "${required_plugins[@]}"; do
  if ! contains_id "${p}" "${ids}"; then
    missing+=("${p}")
  fi
done

bundled_dir_added=false
if (( ${#missing[@]} > 0 )); then
  if bundled_dir="$(resolve_bundled_dir || true)"; then
    if [[ -n "${bundled_dir}" ]]; then
      result="$(python_set_load_path "${bundled_dir}")"
      if [[ "${result}" == "changed" ]]; then
        bundled_dir_added=true
      fi
    fi
  fi
fi

ids="$(get_plugin_ids || true)"
missing=()
for p in "${required_plugins[@]}"; do
  if ! contains_id "${p}" "${ids}"; then
    missing+=("${p}")
  fi
done

if (( ${#missing[@]} > 0 )); then
  echo "Missing required plugins on this host: ${missing[*]}" >&2
  echo "Install/copy them first, then rerun." >&2
  exit 2
fi

python_apply_required "$(IFS=,; echo "${required_plugins[*]}")" >/dev/null
openclaw config validate --json >/dev/null

cat <<EOF
{
  "config_path": "${config_path}",
  "required_plugins": ["${required_plugins[0]}", "${required_plugins[1]}", "${required_plugins[2]}"],
  "bundled_dir_added": ${bundled_dir_added},
  "restart_required": true,
  "restart_cmd": "openclaw gateway stop; OPENCLAW_SKIP_GMAIL_WATCHER=1 openclaw gateway run --bind loopback"
}
EOF
