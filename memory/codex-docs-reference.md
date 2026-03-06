# Codex Docs Knowledge Pack

Synced: March 5, 2026 (America/New_York)

This file is a durable reference distilled from official OpenAI Codex docs.
Use this first for quick recall, then open source pages for exact details.

## Source set ingested

- https://developers.openai.com/codex/config-basic
- https://developers.openai.com/codex/config-advanced
- https://developers.openai.com/codex/config-reference
- https://developers.openai.com/codex/config-sample
- https://developers.openai.com/codex/speed
- https://developers.openai.com/codex/rules
- https://developers.openai.com/codex/guides/agents-md
- https://developers.openai.com/codex/mcp
- https://developers.openai.com/codex/skills
- https://developers.openai.com/codex/multi-agent
- https://developers.openai.com/
- https://developers.openai.com/sitemap-index.xml
- https://developers.openai.com/sitemap-0.xml

Sitemap coverage snapshot:

- sitemap-index points to `sitemap-0.xml`
- `sitemap-0.xml` currently lists 2,839 URLs

## 1) Configuration standard

### 1.1 Config files and precedence

Primary files:

- User config: `~/.codex/config.toml`
- Project config: `.codex/config.toml` (trusted projects only)
- Optional system config: `/etc/codex/config.toml` (Unix)

Resolution order (highest to lowest):

1. CLI flags and `--config` overrides
2. Profile values (`--profile`)
3. Project `.codex/config.toml` layers from repo root to cwd (closest wins)
4. User config
5. System config
6. Built-in defaults

If project trust is `untrusted`, Codex skips project `.codex/` layers.

### 1.2 Core keys worth memorizing

- `model`
- `approval_policy`
- `sandbox_mode`
- `web_search`
- `model_reasoning_effort`
- `model_reasoning_summary`
- `model_verbosity`
- `personality`
- `[shell_environment_policy]`
- `[features]`
- `project_doc_max_bytes`
- `project_doc_fallback_filenames`
- `project_root_markers`

### 1.3 Advanced config patterns

Profiles (experimental):

- Define under `[profiles.<name>]`
- Switch with `codex --profile <name>`
- Can override model, approvals, providers, and model catalog
- Not currently supported in IDE extension

One-off overrides:

- `codex --model gpt-5.4`
- `codex --config model='"gpt-5.4"'`
- `--config` values are TOML, not JSON

Project root detection:

- Default marker is `.git`
- Override with `project_root_markers`
- Empty list means "treat cwd as root"

Providers:

- Use `OPENAI_BASE_URL` for endpoint override without new provider block
- Custom providers via `[model_providers.<id>]`
- Support retries, headers, query params, wire API (`responses` or `chat`)

Observability and controls:

- `[otel]` for OTel logs/metrics export
- `[analytics] enabled = false` to disable metrics collection
- `[feedback] enabled = false` to disable `/feedback`
- `notify = [...]` to call external notifier on events

Runtime quality-of-life:

- `[history] persistence = "none"` to disable local history
- `[history] max_bytes = ...` to cap history file size
- `file_opener` controls clickable citation URI scheme
- `[tui]` controls notifications, animations, alternate screen, tooltips

### 1.4 Feature flags (important families)

Stable/common:

- `collaboration_modes`
- `personality`
- `request_rule`
- `shell_tool`
- `undo`

Experimental/beta to opt into only when needed:

- `multi_agent`
- `apps`
- `apps_mcp_gateway`
- `search_tool`
- `shell_snapshot` (beta)
- `unified_exec` (beta)
- `apply_patch_freeform`
- `remote_models`
- `runtime_metrics`

## 2) Rules standard (.rules)

Location pattern:

- `~/.codex/rules/*.rules` for user scope
- Team config locations also supported

Language and primitive:

- Starlark
- Primary rule function: `prefix_rule(...)`

Key fields:

- `pattern` (required)
- `decision`: `allow` | `prompt` | `forbidden`
- `justification` (optional but recommended)
- `match` / `not_match` tests (strongly recommended)

Decision merge rule:

- Most restrictive wins: `forbidden > prompt > allow`

Shell wrapper behavior:

- For safe linear scripts (simple words + `&&` `||` `;` `|`), Codex splits and evaluates each command
- For advanced shell syntax (redirects, substitutions, vars, globbing, control flow), Codex evaluates wrapper invocation conservatively as one command

Validation command:

- `codex execpolicy check --pretty --rules <file.rules> -- <command ...>`

## 3) AGENTS.md discovery standard

Discovery order:

1. Global: `AGENTS.override.md` then `AGENTS.md` in `CODEX_HOME`
2. Project: for each directory from root to cwd, check `AGENTS.override.md`, then `AGENTS.md`, then fallback filenames
3. Merge in root-to-cwd order; closest directory guidance appears last and overrides earlier guidance

Limits:

- Empty files are skipped
- Combined bytes constrained by `project_doc_max_bytes` (default 32 KiB)

Useful controls:

- `project_doc_fallback_filenames`
- `CODEX_HOME` override for alternate instruction profile

## 4) MCP standard

Supported transports:

- STDIO servers (command + args)
- Streamable HTTP servers (url + auth headers/tokens)

Setup paths:

- CLI: `codex mcp add/list/remove/login/...`
- Config: `[mcp_servers.<id>]` blocks

STDIO fields:

- `command` (required)
- `args`, `env`, `env_vars`, `cwd`

HTTP fields:

- `url` (required)
- `bearer_token_env_var`
- `http_headers`
- `env_http_headers`

Operational controls:

- `startup_timeout_sec`
- `tool_timeout_sec`
- `enabled`
- `required`
- `enabled_tools`
- `disabled_tools`

OAuth controls:

- `mcp_oauth_callback_port`
- `mcp_oauth_callback_url`

## 5) Skills standard

Skill structure:

- Directory with `SKILL.md`
- Optional `scripts/`, `references/`, `assets/`, and metadata file `agents/openai.yaml`

Activation modes:

- Explicit invocation (`$skill-name` or skill picker)
- Implicit invocation based on description match

Discovery scopes:

- Repo: `.agents/skills` from cwd up to repo root
- User: `$HOME/.agents/skills`
- Admin: `/etc/codex/skills`
- System: built-in skills bundled with Codex

Control knobs:

- `[[skills.config]] path = ".../SKILL.md" enabled = false`

Optional metadata via `agents/openai.yaml`:

- UI metadata (display name, icons, brand color)
- Invocation policy (`allow_implicit_invocation`)
- Tool dependencies (for example MCP dependency declarations)

## 6) Multi-agent standard

Enablement:

- Set `[features] multi_agent = true`
- Restart Codex

Built-in role concepts:

- `default`
- `worker`
- `explorer`
- `monitor`

Role config schema:

- `[agents]` for limits: `max_threads`, `max_depth`, `job_max_runtime_seconds`
- `[agents.<name>]` with `description` and optional `config_file`

CSV fanout tool:

- `spawn_agents_on_csv`
- One worker per CSV row
- Workers must call `report_agent_job_result` exactly once
- Results exported with metadata columns (`job_id`, `item_id`, `status`, `last_error`, `result_json`)

Behavior notes:

- Child agents inherit parent sandbox and approval runtime overrides
- Approval prompts can originate from inactive threads in interactive mode

## 7) Speed options

Fast mode:

- Command: `/fast`
- Supports GPT-5.4
- Stated behavior: ~1.5x speed, 2x credit consumption

Codex-Spark:

- Separate model family (`gpt-5.3-codex-spark`)
- Faster and less capable than primary coding model
- Useful for quick iteration and exploration

## 8) requirements.toml governance (admin)

Admin-enforced constraints can restrict:

- Allowed `approval_policy` values
- Allowed `sandbox_mode` values
- Allowed `web_search` modes
- Feature flag allow/deny sets
- MCP identity allowlists
- Enforced restrictive rules

Practical effect:

- Even valid local config values can be blocked by requirements policy on managed machines.

## 9) Docs index memory map

Homepage taxonomy snapshot includes:

- API platform docs and guides
- Codex docs (config, rules, AGENTS, MCP, skills, multi-agent)
- Apps SDK docs
- Cookbook, videos, blog, changelog, and release streams

Sitemap snapshot (`sitemap-0.xml`) contains broad API/docs/reference coverage, including:

- API guides across tools, models, evals, realtime, safety, optimization
- API reference trees (REST and SDK references)
- Codex section pages and release material

## 10) Quick retrieval protocol (for future turns)

When asked for Codex/OpenAI docs guidance:

1. Check this file first for fast orientation.
2. Verify against current official page before giving final answer.
3. Use exact URLs in responses when operational details matter.
4. Treat cached or summarized guidance as stale unless date-verified.