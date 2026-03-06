## Long-term Memory

### 2026-03-05 Codex standardization baseline

- Standardized workspace instructions to Codex-aligned syntax and precedence model.
- Primary instruction files now follow ISO-CODEX-2026-03-06 structure.
- Canonical quick-reference for Codex docs is stored in:
  - `memory/codex-docs-reference.md`
- Docs index ingestion source chain:
  - `https://developers.openai.com/`
  - `https://developers.openai.com/sitemap-index.xml`
  - `https://developers.openai.com/sitemap-0.xml`

### Fleet operations memory

- Restart/resync failure root cause: `pkill -f openclaw-gateway` matched its own wrapper command.
- Durable fix: use `pkill -f '[o]penclaw-gateway'` in orchestrator restart/resync steps.
- After patch, both workers restart and handshake cleanly.

### 2026-03-05 Codex docs memory expansion

- Expanded durable docs memory into `memory/codex-docs-reference.md` with page-by-page standards for config, rules, AGENTS discovery, MCP, skills, multi-agent, speed, and requirements governance.
- Added docs index snapshot details from `sitemap-index.xml` and `sitemap-0.xml` (2,839 URLs at sync time).
- Synced the same knowledge pack into `C:/development/memory/codex-docs-reference.md` for cross-workspace reuse.

### 2026-03-05 Fleet API health model
- Added explicit fleet health endpoint and evaluator (`/v1/fleet/health`) with acceptance checks for pairing, worker process/corpus state, recent handshake/local-gateway signals, and post-success critical error detection.
- Fleet status collection now runs worker probes in parallel to reduce orchestration latency and isolate per-worker probe failures.

### 2026-03-06 Fleet delegation and postback enforcement
- Instruction standard now explicitly requires fleet delegation for every non-trivial process by default.
- Worker completion now requires visible full-body chat postback; header-only markers are treated as invalid completion.
- Reporting chain requirement added: every delegated task must specify designated recipients before execution.
- Added orchestration foundation spec for provider-agnostic plug-and-play orchestration with worker groups, job templates/runs, and delivery routing.

### 2026-03-06 Canonical instruction source cleanup
- Project root `AGENTS.md` is now the single authoritative instruction/configuration source.
- Legacy policy files under `AGENTS/` were converted to compatibility stubs pointing to root `AGENTS.md`.
- `.codex/environments/environment.toml` now bootstraps from `/AGENTS.md`.
- `C:/development` instruction copies are marked as non-authoritative compatibility mirrors to avoid policy drift.

### 2026-03-06 Protocol R&D and full audit trail baseline
- Added protocol governance spec for ORDL-native standards and conformance workflow.
- Added full audit trail spec requiring actor-complete and chain-verifiable events.
- Backend now exposes structured audit events and verification endpoints (`/v1/audit/events`, `/v1/audit/verify`) with passing tests.
