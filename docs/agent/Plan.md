# Plan.md — Durable Execution Plan

This file is the source of truth for active long-horizon work.

## Task

Short name: MCP dev-tooling setup (shared Codex + Claude)

Related specification:

- `docs/agent/Prompt.md`
- `docs/MCP_SETUP_GUIDE.md`
- Plan of record: `/Users/zhang/.claude/plans/fancy-dancing-marble.md`

## How to use this plan

- For quick standalone answers or small bounded edits, follow `AGENTS.md` Mode 1.
- For durable work, follow `AGENTS.md` Mode 2 and fill in this file before implementation.
- For harness or agent-policy changes, follow `AGENTS.md` Mode 3.
- Keep `Status.md` short; keep execution detail in `Implement.md`; keep long notes in `Documentation.md`.

## Current milestone

Milestone: Dev MCP servers installed and shared between Codex and Claude.

Status: `done`

Next action: Start the disclosure-anchor service code.

## Progress

- Installed standalone Node v24.16.0 → `~/.local/node` (+ `~/.local/bin` symlinks).
- Warmed shared `~/.npm` cache (pinned packages) + Playwright Chromium.
- Wrote `.mcp.json` (context7, playwright, dbhub) — all ✔ Connected.
- Added context7 + playwright to global `~/.codex/config.toml`; dbhub kept project-local via
  project-scoped `<repo>/.codex/config.toml` (deep-merged over global for this trusted project).
- Wrote `dbhub.toml` (read-only ledger) + `docs/MCP_SETUP_GUIDE.md`; updated `.env.template`, `.gitignore`.

## Active working checklist

- [x] Resolve Node runtime (installed standalone Node).
- [x] Write/validate Claude `.mcp.json` + Codex `config.toml` (identical npx, shared cache).
- [x] DBHub read-only ledger via `dbhub.toml`; smoke EXIT 0.
- [x] Setup guide + env/gitignore updates.
- [x] Validation: configs parse; `claude mcp list` all Connected.
- [x] Independent review gate (Claude read-only reviewer; quanti_reviewer is Codex-only) — pass_with_items, fixes applied.

## Surprises & Discoveries

- No system Node/npm/npx on this machine (no Homebrew/nvm) — only Codex.app's bundled Node + `uv`.
  Resolved by installing standalone Node to `~/.local`.
- DBHub 0.22.x removed the `--readonly` CLI flag → moved to `dbhub.toml` `[[tools]] readonly = true`.
- `.mcp.json` and `.codex/config.toml` are gitignored (machine-specific) — configs are not committed.
- Codex MCP config is NOT global-only (earlier assumption): it supports project-scoped
  `<repo>/.codex/config.toml` for trusted projects, deep-merged over `~/.codex/config.toml`.
  dbhub moved there 2026-06-15 for symmetry with Claude's `.mcp.json`.

## Validation

- JSON/TOML parse of `.mcp.json`, `~/.codex/config.toml`, `dbhub.toml`, `.claude/settings.local.json`.
- `claude mcp list` → context7 / playwright / dbhub all ✔ Connected.
- DBHub read-only smoke vs `/Volumes/AgentSSD/disclosure_anchor/ledger.db` → EXIT 0, `🔒 execute_sql`.

## Decision log

- No data MCPs; data service is the project's own code. (user direction)
- Plan A: shared npm cache + pinned versions (vs Plan B pinned-dir install). (user choice)
- Standalone Node install (vs bundled Codex node / all-uvx). (user choice)
- dbhub project-local only — Claude `.mcp.json` + Codex project-scoped `<repo>/.codex/config.toml`
  (not global); GitHub omitted (Codex plugin + `gh`). (implementation call, documented)

## Outcomes & Retrospective

- Milestone complete: 3 dev MCPs (context7/playwright/dbhub) shared between Codex and Claude via a
  standalone Node + shared npm cache; independent review passed with minor fixes applied.
- Next focus: the disclosure-anchor service code itself (no MCP dependency in the data path).
