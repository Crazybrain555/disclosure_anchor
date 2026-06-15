# Documentation.md — Durable Audit Log And Operator Notes

This file is the long-form memory for future durable work. Keep `Status.md` short.

## Current baseline

Codex / Claude harness baseline plus a configured set of **dev-facing MCP servers** for building
the disclosure-anchor (L1) service. The data service itself is the project's own Python code.

## Decisions

- **No data MCPs.** disclosure-anchor is an independently-coded data service (cninfo/HKEX scrape,
  PDF download, provenance, Docling/MinerU parse, SQLite/DuckDB ledger → AgentSSD). MCPs only
  *help develop* it. Dropped all akshare/tushare/cninfo/financial MCP ideas.
- **Active dev MCPs (pinned):** context7 `@upstash/context7-mcp@3.2.1`, playwright
  `@playwright/mcp@0.0.76`, dbhub `@bytebase/dbhub@0.22.3`. GitHub omitted (Codex has the `github`
  plugin; Claude has `gh`).
- **Install = Plan A** (shared npm cache, `npx -y pkg@pinned`). The "public place both share" is the
  per-user `~/.npm` cache (content-addressed, no time TTL); pinned versions prevent drift.
- **Runtime:** machine had no system Node — installed standalone Node **v24.16.0** to `~/.local/node`
  with symlinks in `~/.local/bin` (on PATH next to `uv`). Both harnesses use it.
- **dbhub** uses `dbhub.toml` (0.22.x dropped `--readonly`) with a read-only `execute_sql` over the
  AgentSSD ledger. Kept **project-local** in both harnesses: Claude `.mcp.json` and Codex
  **project-scoped** `<repo>/.codex/config.toml` (NOT the global `~/.codex/config.toml`), because the
  DSN is project-specific. Codex deep-merges the project layer on top of global for trusted projects.
- **Gitignored machine-specific files:** `.mcp.json`, `.codex/config.toml`, `dbhub.toml`. Secrets via
  shell env only; Context7 runs keyless if `CONTEXT7_API_KEY` is unset.

## Validation history

- 2026-06-15: all configs parse (JSON/TOML); `claude mcp list` → context7/playwright/dbhub ✔ Connected;
  DBHub read-only smoke vs `/Volumes/AgentSSD/disclosure_anchor/ledger.db` → EXIT 0; Node v24.16.0 + npx OK.
- 2026-06-15 (project-scoped Codex MCP): created `<repo>/.codex/config.toml` with `[mcp_servers.dbhub]`;
  `.codex/config.toml` parses; `codex mcp list` from repo → context7/playwright/node_repl/computer-use **+ dbhub**;
  from `~` → dbhub absent (project-scoped confirmed). Live MCP smoke (Claude session): context7 `resolve-library-id`,
  dbhub `SELECT sqlite_version()`→3.53.0 / `SELECT 1+1`→2, playwright navigate example.org all OK.

## Review history

- 2026-06-15: independent read-only review (Claude reviewer, since `quanti_reviewer` is Codex-only)
  = **pass_with_items**, high confidence, no Critical/Major. 3 minor findings fixed: (1) clarified the
  DBHub DSN slash comment in SETUP_GUIDE §5; (2) added a defensive note on the `.codex/config.toml`
  gitignore line; (3) annotated unused Alpaca keys in `.env.template`. Confirmed: no secrets in
  committed files; `.mcp.json`/`.codex/config.toml`/`dbhub.toml` are gitignored & untracked.

## Known follow-ups

- Point DBHub DSN at the real ledger path once the service defines its schema/layout on AgentSSD.
- Tier-2 MCPs (DuckDB, filesystem, sequential-thinking, web) are documented but not enabled.
- ~~If Codex gains project-scoped MCP config, move dbhub there for symmetry with Claude.~~
  **Done 2026-06-15:** Codex supports project-scoped `.codex/config.toml` (trusted projects, deep-merged
  over global). Moved dbhub into `<repo>/.codex/config.toml`; verified project-scoped via `codex mcp list`.
