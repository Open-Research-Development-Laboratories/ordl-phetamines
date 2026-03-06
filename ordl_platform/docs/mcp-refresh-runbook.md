# MCP Refresh Runbook

Use this when MCP servers are configured but not visible to the runtime.

## 1) Verify local config

PowerShell:

```powershell
Get-Content "$env:USERPROFILE\.codex\config.toml"
```

Confirm expected servers are `enabled = true`.

## 2) Validate host tooling

```powershell
node --version
npx --version
uvx --version
```

## 3) Probe server binaries directly

```powershell
npx -y @upstash/context7-mcp@latest --help
npx -y @modelcontextprotocol/server-sequential-thinking --help
uvx mcp-server-fetch --help
```

## 4) Restart Codex app session

- Fully close the Codex desktop app.
- Re-open app and reopen this workspace.
- Re-check MCP availability.

## 5) If handshake still fails

- Disable failing server entries temporarily in `config.toml`.
- Restart Codex.
- Re-enable one server at a time to isolate failure.

## 6) Fleet-first fallback

If MCP remains unavailable, continue with local tools and fleet dispatch routes while logging the MCP outage in session notes.
