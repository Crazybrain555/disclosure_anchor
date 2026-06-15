# Status.md — Durable Current State

Keep this file short. Read it first when continuing durable work.

## Current task identity

Task: MCP dev-tooling setup for disclosure-anchor (Mode 3 — harness/config maintenance).

## Current state

Current milestone: Dev MCP servers installed and shared between Codex and Claude.

Status: `done`

One-sentence summary:
Installed a standalone Node runtime and wired three dev-facing MCP servers (context7, playwright, dbhub) shared via the npm cache between Claude (`.mcp.json`) and Codex (global `~/.codex/config.toml` for context7/playwright + project-scoped `<repo>/.codex/config.toml` for dbhub); no data MCPs — the disclosure data service stays the project's own code.

Next action:
Milestone complete. Begin the actual disclosure-anchor service code (cninfo/HKEX scrape → PDF archive → Docling/MinerU parse → ledger on AgentSSD).

## Current blockers

- None.

## Latest validation

- `.mcp.json`, `~/.codex/config.toml`, `<repo>/.codex/config.toml`, `dbhub.toml`, `.claude/settings.local.json` all parse (JSON/TOML).
- `claude mcp list` → context7 / playwright / dbhub all ✔ Connected.
- `codex mcp list` from repo → context7 / playwright / node_repl / computer-use **+ dbhub**; from `~` → dbhub absent (project-scoped).
- DBHub read-only smoke against `/Volumes/AgentSSD/disclosure_anchor/ledger.db` → EXIT 0, `🔒 execute_sql`.
- Codex MCP exposure verified from repo: `context7`, `playwright`, and project-scoped `dbhub` are enabled;
  `dbhub` is scoped to `<repo>/.codex/config.toml` with only `execute_sql` exposed.
- `node -v` = v24.16.0; `npx`/`uvx` resolve from `~/.local/bin`.

## Review state

Latest independent review: 2026-06-15 — independent read-only review = pass_with_items (no Critical/Major). 3 minor findings, all addressed (DSN comment clarified, .gitignore note added, .env.template Alpaca annotated). Note: ran a Claude read-only reviewer since `quanti_reviewer` is a Codex-only subagent.

## Continuation instructions

1. Read `AGENTS.md`.
2. Read this file.
3. Read `docs/agent/Plan.md`.
4. Read `docs/agent/Implement.md`.
5. MCP setup details live in `docs/MCP_SETUP_GUIDE.md`; machine-specific configs (`.mcp.json`, `.codex/config.toml`, `dbhub.toml`) are gitignored.
